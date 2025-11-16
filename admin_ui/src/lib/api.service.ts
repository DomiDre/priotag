import { authStore } from '$lib/auth.stores';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import type { WeekPriority } from '$lib/priorities.types';
import { env } from '$env/dynamic/public';
import type {
	VacationDayAdmin,
	VacationDayCreate,
	VacationDayUpdate,
	BulkVacationDayCreate,
	BulkVacationDayResponse
} from '$lib/vacation-days.types';

export class ApiService {
	public baseUrl: string;

	constructor() {
		this.baseUrl = import.meta.env.DEV
			? 'http://localhost:8000/api/v1'
			: env.PUBLIC_BACKEND_URL
				? `${env.PUBLIC_BACKEND_URL}/api/v1`
				: '/api/v1';
	}

	async healthCheck(): Promise<boolean> {
		try {
			const response = await fetch(`${this.baseUrl}/health`, {
				method: 'GET',
				signal: AbortSignal.timeout(5000)
			});
			return response.ok;
		} catch {
			return false;
		}
	}

	private async request(endpoint: string, options: RequestInit = {}) {
		const config: RequestInit = {
			...options,
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			}
		};

		const response = await fetch(`${this.baseUrl}${endpoint}`, config);

		// Handle 401 Unauthorized - session expired
		if (response.status === 401) {
			// Clear auth state (don't call logout endpoint - already unauthorized)
			authStore.clearAuth(false);

			// Only redirect if not already on login page (prevent loop)
			if (browser && window.location.pathname !== '/login') {
				await goto('/login', { replaceState: true });
			}
			throw new Error('Sitzung abgelaufen. Bitte melden Sie sich erneut an.');
		}

		// Handle 403 Forbidden
		if (response.status === 403) {
			throw new Error('Keine Berechtigung für diese Aktion.');
		}

		// Handle rate limiting
		if (response.status === 429) {
			const data = await response.json();
			throw new Error(data.detail || 'Zu viele Anfragen. Bitte versuchen Sie es später erneut.');
		}

		if (!response.ok) {
			const data = await response.json();
			throw new Error(data.detail || 'Ein Fehler ist aufgetreten');
		}

		return response;
	}

	private async requestJson(endpoint: string, options: RequestInit = {}) {
		const response = await this.request(endpoint, options);
		return response.json();
	}

	// ==================== Authentication ====================

	async login(identity: string, password: string, keepLoggedIn: boolean) {
		const response = await this.requestJson('/auth/login', {
			method: 'POST',
			body: JSON.stringify({
				identity,
				password,
				keep_logged_in: keepLoggedIn
			})
		});

		// Update auth store (cookies are set automatically by server)
		authStore.setAuth();

		return response;
	}

	async logout() {
		try {
			await this.requestJson('/auth/logout', {
				method: 'POST'
			});
		} catch (error) {
			console.error('Logout error:', error);
		}

		// Clear auth without calling logout endpoint again
		authStore.clearAuth(false);
	}

	async verify() {
		const response = await this.requestJson('/auth/verify', {
			method: 'GET'
		});
		return response;
	}

	async changePassword(currentPassword: string, newPassword: string) {
		const response = await this.requestJson('/auth/change-password', {
			method: 'POST',
			body: JSON.stringify({
				current_password: currentPassword,
				new_password: newPassword
			})
		});

		// Password change invalidates all sessions
		authStore.clearAuth(false);
		if (browser) {
			await goto('/login', { replaceState: true });
		}

		return response;
	}

	// ==================== Admin Endpoints ====================

	async getMagicWordInfo() {
		return this.requestJson('/admin/magic-word-info', {
			method: 'GET'
		});
	}

	async updateMagicWord(newMagicWord: string) {
		return this.requestJson('/admin/update-magic-word', {
			method: 'POST',
			body: JSON.stringify({ new_magic_word: newMagicWord })
		});
	}

	async getTotalUsers() {
		return this.requestJson('/admin/total-users', {
			method: 'GET'
		});
	}

	async getUserSubmissions(month: string) {
		return this.requestJson(`/admin/users/${month}`, {
			method: 'GET'
		});
	}

	async getManualSubmissions(month: string) {
		return this.requestJson(`/admin/manual-entries/${month}`, {
			method: 'GET'
		});
	}

	async submitManualPriority(identifier: string, month: string, weeks: WeekPriority[]) {
		return this.requestJson('/admin/manual-priority', {
			method: 'POST',
			body: JSON.stringify({
				identifier,
				month,
				weeks
			})
		});
	}

	async deleteManualEntry(month: string, identifier: string) {
		return this.requestJson(`/admin/manual-entry/${month}/${identifier}`, {
			method: 'DELETE'
		});
	}

	// ==================== User Management ====================

	async getUserDetail(userId: string) {
		return this.requestJson(`/admin/users/detail/${userId}`, {
			method: 'GET'
		});
	}

	async updateUser(
		userId: string,
		data: { username?: string; email?: string; role?: string }
	): Promise<{ success: boolean; message: string }> {
		return this.requestJson(`/admin/users/${userId}`, {
			method: 'PUT',
			body: JSON.stringify(data)
		});
	}

	async deleteUser(
		userId: string
	): Promise<{ success: boolean; message: string; deletedPriorities: number }> {
		return this.requestJson(`/admin/users/${userId}`, {
			method: 'DELETE'
		});
	}

	// ==================== Priority Management ====================

	async updatePriority(
		priorityId: string,
		encryptedFields: string
	): Promise<{ success: boolean; message: string }> {
		return this.requestJson(`/admin/priorities/${priorityId}`, {
			method: 'PATCH',
			body: JSON.stringify({ encrypted_fields: encryptedFields })
		});
	}

	async deletePriority(priorityId: string): Promise<{ success: boolean; message: string }> {
		return this.requestJson(`/admin/priorities/${priorityId}`, {
			method: 'DELETE'
		});
	}

	// ==================== Vacation Days ====================

	async createVacationDay(data: VacationDayCreate): Promise<VacationDayAdmin> {
		return this.requestJson('/admin/vacation-days', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async bulkCreateVacationDays(data: BulkVacationDayCreate): Promise<BulkVacationDayResponse> {
		return this.requestJson('/admin/vacation-days/bulk', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async getVacationDays(params?: { year?: number; type?: string }): Promise<VacationDayAdmin[]> {
		const queryParams = new URLSearchParams();
		if (params?.year) queryParams.append('year', params.year.toString());
		if (params?.type) queryParams.append('type', params.type);

		const query = queryParams.toString();
		const endpoint = `/admin/vacation-days${query ? `?${query}` : ''}`;

		return this.requestJson(endpoint, {
			method: 'GET'
		});
	}

	async getVacationDay(date: string): Promise<VacationDayAdmin> {
		return this.requestJson(`/admin/vacation-days/${date}`, {
			method: 'GET'
		});
	}

	async updateVacationDay(date: string, data: VacationDayUpdate): Promise<VacationDayAdmin> {
		return this.requestJson(`/admin/vacation-days/${date}`, {
			method: 'PUT',
			body: JSON.stringify(data)
		});
	}

	async deleteVacationDay(date: string): Promise<{ success: boolean; message: string }> {
		return this.requestJson(`/admin/vacation-days/${date}`, {
			method: 'DELETE'
		});
	}
}

export const apiService = new ApiService();
