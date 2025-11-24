import { authStore } from '$lib/auth.store';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import type { PriorityResponse, WeekData } from '$lib/priorities.types';
import type { VacationDay } from '$lib/vacation-days.types';

export class ApiService {
	public baseUrl: string;

	constructor() {
		this.baseUrl = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1';
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

			// Only redirect if not already on login/register page (prevent loop)
			const currentPath = browser ? window.location.pathname : '';
			if (browser && currentPath !== '/login' && currentPath !== '/register') {
				goto('/login', { replaceState: true });
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

	// ==================== Institutions ====================
	// Note: Public institution listing removed for security reasons.
	// Institutions are now selected via URL parameters in registration links.

	// ==================== Authentication ====================

	async verifyMagicWord(magicWord: string, institutionShortCode: string) {
		return this.requestJson('/auth/verify-magic-word', {
			method: 'POST',
			body: JSON.stringify({
				magic_word: magicWord,
				institution_short_code: institutionShortCode
			})
		});
	}

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

	async register(data: {
		identity: string;
		password: string;
		passwordConfirm: string;
		name: string;
		registration_token: string;
		keep_logged_in: boolean;
	}) {
		const response = await this.requestJson('/auth/register', {
			method: 'POST',
			body: JSON.stringify({
				...data
			})
		});

		// Update auth store
		authStore.setAuth();

		return response;
	}

	async registerWithQR(data: {
		identity: string;
		password: string;
		passwordConfirm: string;
		name: string;
		magic_word: string;
		institution_short_code: string;
		keep_logged_in: boolean;
	}) {
		const response = await this.requestJson('/auth/register-qr', {
			method: 'POST',
			body: JSON.stringify({
				...data
			})
		});

		// Update auth store
		authStore.setAuth();

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

		// Backend updates auth cookies with new token and DEK
		// User stays logged in with new credentials
		return response;
	}

	// ==================== Account & GDPR ====================

	async getAccountInfo() {
		return this.requestJson('/account/info', {
			method: 'GET'
		});
	}

	async getUserData() {
		return this.requestJson('/account/data', {
			method: 'GET'
		});
	}

	async deleteAllUserData() {
		return this.requestJson('/account/delete', {
			method: 'DELETE'
		});
	}

	// ==================== Priorities ====================

	async getPriorities(month?: string): Promise<PriorityResponse> {
		const endpoint = month ? `/priorities/${month}` : '/priorities';
		return this.requestJson(endpoint, {
			method: 'GET'
		});
	}

	async updatePriority(month: string, priorityData: WeekData[]) {
		// Single retry for rate limiting with appropriate delay
		const maxRetries = 1;
		let lastError: Error | null = null;

		for (let attempt = 0; attempt <= maxRetries; attempt++) {
			try {
				return await this.requestJson(`/priorities/${month}`, {
					method: 'PUT',
					body: JSON.stringify(priorityData)
				});
			} catch (error) {
				// Check if it's a rate limit error (concurrent save in progress)
				if (error instanceof Error && error.message.includes('Bitte warten Sie einen Moment')) {
					lastError = error;

					// Only retry once after waiting for the lock to clear
					if (attempt < maxRetries) {
						// Wait 3.5 seconds for backend lock to clear
						await new Promise((resolve) => setTimeout(resolve, 3500));
						continue;
					}
				}

				// If it's not a rate limit error, throw immediately
				throw error;
			}
		}

		// If retry failed, throw informative error
		throw lastError || new Error('Fehler beim Speichern der Prioritäten');
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

	async getUserSubmissions(month: string) {
		return this.requestJson(`/admin/users/${month}`, {
			method: 'GET'
		});
	}

	// ==================== Vacation Days ====================

	async getVacationDays(params?: {
		year?: number;
		month?: number;
		type?: string;
	}): Promise<VacationDay[]> {
		const queryParams = new URLSearchParams();
		if (params?.year) queryParams.append('year', params.year.toString());
		if (params?.month) queryParams.append('month', params.month.toString());
		if (params?.type) queryParams.append('type', params.type);

		const query = queryParams.toString();
		const endpoint = `/vacation-days${query ? `?${query}` : ''}`;

		return this.requestJson(endpoint, {
			method: 'GET'
		});
	}

	async getVacationDaysInRange(
		startDate: string,
		endDate: string,
		type?: string
	): Promise<VacationDay[]> {
		const queryParams = new URLSearchParams({
			start_date: startDate,
			end_date: endDate
		});
		if (type) queryParams.append('type', type);

		return this.requestJson(`/vacation-days/range?${queryParams.toString()}`, {
			method: 'GET'
		});
	}

	async getVacationDay(date: string): Promise<VacationDay> {
		return this.requestJson(`/vacation-days/${date}`, {
			method: 'GET'
		});
	}
}

export const apiService = new ApiService();
