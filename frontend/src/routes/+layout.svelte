<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/auth.store';
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { initI18n } from '$i18n/i18n-setup';
	import { setLocale } from '$i18n/i18n-svelte';
	import { LL } from '$i18n/i18n-svelte';

	let { children } = $props();

	let isInitializing = $state(true);
	let isVerifying = $state(false);

	// Public routes that don't require authentication
	const publicRoutes = ['/login', '/register', '/imprint', '/privacy'];

	onMount(async () => {
		// Initialize i18n first
		const detectedLocale = await initI18n();
		setLocale(detectedLocale);

		// Prevent concurrent auth checks
		if (isVerifying) return;
		const currentPath = window.location.pathname;
		const isPublicRoute = publicRoutes.includes(currentPath);
		const isRootPath = currentPath === '/';

		if (isRootPath) {
			isInitializing = false;
			return;
		}

		isVerifying = true;

		try {
			// Verify session with server (checks httpOnly cookies)
			const isValid = await authStore.verifyAuth();
			if (!isValid && !isPublicRoute) {
				// Not authenticated and trying to access protected route
				await goto('/login', { replaceState: true });
			} else if (isValid && currentPath === '/login') {
				// Already authenticated on login page
				await goto('/priorities', { replaceState: true });
			}
		} catch {
			// On error, redirect to login for safety
			if (window.location.pathname !== '/login' && window.location.pathname !== '/') {
				await goto('/login', { replaceState: true });
			}
		} finally {
			isInitializing = false;
			isVerifying = false;
		}
	});

</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if isInitializing}
	<div class="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
		<div class="text-center">
			<div
				class="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"
			></div>
			<p class="text-gray-600 dark:text-gray-400">{$LL.common.loading()}</p>
		</div>
	</div>
{:else}
	{@render children?.()}
{/if}
