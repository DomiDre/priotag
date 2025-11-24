import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { apiService } from '$lib/api.service';

interface AuthState {
	isAuthenticated: boolean;
	userId?: string;
	username?: string;
	isAdmin?: boolean;
	role?: 'user' | 'institution_admin' | 'super_admin';
	institutionId?: string;
}

function createAuthStore() {
	const initialState: AuthState = {
		isAuthenticated: false
	};

	// On page load, check if we have a stored security mode
	// actual auth is verified via API call
	if (browser) {
		const wasAuthenticated = sessionStorage.getItem('was_authenticated');
		if (wasAuthenticated === 'true') {
			initialState.isAuthenticated = true; // Tentative - will verify via API
		}
	}

	const { subscribe, set } = writable<AuthState>(initialState);

	// Track if we're currently verifying to prevent concurrent calls
	let isVerifying = false;

	return {
		subscribe,

		/**
		 * Set authentication state after successful login
		 */
		setAuth: (userInfo?: {
			userId: string;
			username: string;
			role: 'user' | 'institution_admin' | 'super_admin';
			institutionId?: string;
		}) => {
			if (browser) {
				sessionStorage.setItem('was_authenticated', 'true');
			}

			set({
				isAuthenticated: true,
				userId: userInfo?.userId,
				username: userInfo?.username,
				isAdmin: userInfo?.role === 'institution_admin' || userInfo?.role === 'super_admin',
				role: userInfo?.role,
				institutionId: userInfo?.institutionId
			});
		},

		/**
		 * Clear authentication state and optionally call logout endpoint
		 * @param callLogoutEndpoint - Whether to call the API logout endpoint (default: true)
		 */
		clearAuth: async (callLogoutEndpoint: boolean = true) => {
			if (browser) {
				// Clear local state
				sessionStorage.removeItem('was_authenticated');

				// Call logout endpoint to clear httpOnly cookies
				// Only if explicitly requested (not on failed auth verification)
				if (callLogoutEndpoint) {
					try {
						await apiService.logout();
					} catch (error) {
						console.error('Logout request failed:', error);
						// Continue anyway - clear local state
					}
				}
			}

			set({
				isAuthenticated: false
			});
		},

		/**
		 * Verify authentication status with server
		 * Call this on app initialization to check if session is still valid
		 */
		verifyAuth: async () => {
			if (!browser) return false;

			// Prevent concurrent verification calls
			if (isVerifying) {
				console.log('Auth verification already in progress, skipping');
				return false;
			}

			isVerifying = true;

			try {
				const data = await apiService.verify();
				if (!data['is_admin']) {
					console.info('No access rights');
					await authStore.clearAuth(false);
					return false;
				}

				const role = data['role'] as 'user' | 'institution_admin' | 'super_admin' | undefined;

				set({
					isAuthenticated: true,
					userId: data['user_id'],
					username: data['username'],
					isAdmin: data['is_admin'],
					role: role,
					institutionId: data['institution_id']
				});
				sessionStorage.setItem('was_authenticated', 'true');
				return true;
			} catch {
				console.info('Auth verification failed - user is not logged in.');
				// Don't call logout endpoint on failed verification (already logged out)
				await authStore.clearAuth(false);
				return false;
			} finally {
				isVerifying = false;
			}
		}
	};
}

export const authStore = createAuthStore();

// ============================================================================
// DERIVED STORES
// ============================================================================

export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);

export const currentUser = derived(authStore, ($auth) => ({
	userId: $auth.userId,
	username: $auth.username,
	isAdmin: $auth.isAdmin,
	role: $auth.role,
	institutionId: $auth.institutionId,
	isSuperAdmin: $auth.role === 'super_admin',
	isInstitutionAdmin: $auth.role === 'institution_admin'
}));
