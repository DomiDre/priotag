<!-- src/routes/register/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { authStore, isAuthenticated } from '$lib/auth.store';
	import { apiService } from '$lib/api.service';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { LL } from '$i18n/i18n-svelte';

	let username = $state('');
	let password = $state('');
	let passwordConfirm = $state('');
	let fullName = $state('');
	let magicWord = $state('');
	let institutionShortCode = $state('');
	let keepLoggedIn = $state(false);
	let error = $state('');
	let loading = $state(false);
	let registrationToken = $state('');
	let magicWordVerified = $state(false);
	let isQRMode = $state(false); // Track if using QR code registration
	let missingInstitution = $state(false); // Track if institution parameter is missing

	$effect(() => {
		if ($isAuthenticated) {
			goto('/');
		}
	});

	// Check for magic word and institution in URL query parameters
	$effect(() => {
		const magicFromUrl = $page.url.searchParams.get('magic');
		const institutionFromUrl = $page.url.searchParams.get('institution');

		// Require institution parameter - redirect to info page if missing
		if (!institutionFromUrl) {
			missingInstitution = true;
			// Redirect to info page after a brief moment to show error
			setTimeout(() => {
				goto('/register-info');
			}, 2000);
			return;
		}

		institutionShortCode = institutionFromUrl;

		// If magic word is also provided (QR code flow), auto-fill and verify
		if (magicFromUrl) {
			magicWord = magicFromUrl;
			magicWordVerified = true;
			isQRMode = true;
		}
	});

	async function handleMagicWord(event: Event) {
		event.preventDefault();
		error = '';
		loading = true;

		try {
			const data = await apiService.verifyMagicWord(magicWord, institutionShortCode);
			registrationToken = data.token;
			magicWordVerified = true;
			error = '';
		} catch (err) {
			error = (err as Error).message;
		} finally {
			loading = false;
		}
	}

	async function handleRegister(event: Event) {
		event.preventDefault();

		error = '';
		loading = true;

		// Basic validation
		if (password !== passwordConfirm) {
			error = $LL.auth.register.errorPasswordMismatch();
			loading = false;
			return;
		}
		if (password.length < 1) {
			error = $LL.auth.register.errorPasswordTooShort();
			loading = false;
			return;
		}

		try {
			// Use QR endpoint if magic word came from URL, otherwise use traditional two-step flow
			if (isQRMode) {
				await apiService.registerWithQR({
					identity: username,
					password,
					passwordConfirm: password,
					name: fullName,
					magic_word: magicWord,
					institution_short_code: institutionShortCode,
					keep_logged_in: keepLoggedIn
				});
			} else {
				await apiService.register({
					identity: username,
					password,
					passwordConfirm: password,
					name: fullName,
					registration_token: registrationToken,
					keep_logged_in: keepLoggedIn
				});
			}
			if (await authStore.verifyAuth()) goto('/priorities');
		} catch (err) {
			error = (err as Error).message;
			// If token expired or magic word invalid, reset to magic word step
			if (error.includes('token') || error.includes('Zauberwort')) {
				magicWordVerified = false;
				registrationToken = '';
				if (!isQRMode) {
					magicWord = '';
				}
			}
		} finally {
			loading = false;
		}
	}

	function goToLogin() {
		goto('/login');
	}

	function resetToMagicWord() {
		magicWordVerified = false;
		registrationToken = '';
		if (!isQRMode) {
			magicWord = '';
		}
		error = '';
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Language Switcher -->
		<div class="mb-4 flex justify-end">
			<LanguageSwitcher />
		</div>

		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">
				{$LL.auth.register.title()}
			</h1>
			<p class="text-gray-600 dark:text-gray-300">
				{magicWordVerified ? $LL.auth.register.subtitle() : $LL.auth.register.subtitleMagicWord()}
			</p>
		</div>

		<!-- Main Card -->
		<div class="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if missingInstitution}
				<!-- Missing Institution Error -->
				<div class="text-center">
					<div
						class="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20"
					>
						<span class="text-3xl">⚠️</span>
					</div>
					<h2 class="mb-4 text-xl font-semibold text-gray-800 dark:text-white">
						Missing Registration Link
					</h2>
					<p class="mb-4 text-gray-600 dark:text-gray-300">
						You need a valid registration link from your institution to register.
					</p>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Redirecting to registration information...
					</p>
				</div>
			{:else if !magicWordVerified}
				<!-- Magic Word Form -->
				<form class="space-y-6" onsubmit={handleMagicWord}>
					<div class="mb-4 text-center">
						<div
							class="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500"
						>
							<span class="text-3xl">🔐</span>
						</div>
						<h2 class="text-xl font-semibold text-gray-800 dark:text-white">
							{$LL.auth.register.accessVerification()}
						</h2>
						<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
							{$LL.auth.register.magicWordInfo()}
						</p>
					</div>

					<div>
						<label
							for="magicWord"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							{$LL.auth.register.magicWord()}
						</label>
						<input
							id="magicWord"
							type="text"
							bind:value={magicWord}
							required
							disabled={loading}
							placeholder={$LL.auth.register.magicWordPlaceholder()}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					{#if error}
						<div
							class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
						>
							<div class="flex items-start">
								<svg
									class="mr-2 h-5 w-5 flex-shrink-0 text-red-600"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
										clip-rule="evenodd"
									/>
								</svg>
								<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
							</div>
						</div>
					{/if}

					<button
						type="submit"
						disabled={loading || !magicWord || !institutionShortCode}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4
							   font-semibold text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
					>
						{#if loading}
							<span class="mr-2 animate-spin">⟳</span>
						{/if}
						{loading ? $LL.auth.register.verifying() : $LL.auth.register.verifyMagicWord()}
					</button>
				</form>
			{:else}
				<!-- Registration Form -->
				<form class="space-y-6" onsubmit={handleRegister}>
					<div
						class="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-900/20"
					>
						<p class="flex items-center text-sm text-green-700 dark:text-green-400">
							<span class="mr-2">{isQRMode ? '📱' : '✓'}</span>
							{isQRMode ? $LL.auth.register.qrCodeDetected() : $LL.auth.register.verified()}
						</p>
					</div>

					<!-- Privacy Info Banner -->
					<div
						class="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20"
					>
						<div class="flex items-start">
							<svg
								class="mr-2 h-5 w-5 flex-shrink-0 text-blue-600 dark:text-blue-400"
								fill="currentColor"
								viewBox="0 0 20 20"
							>
								<path
									fill-rule="evenodd"
									d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
									clip-rule="evenodd"
								/>
							</svg>
							<div class="text-sm text-blue-800 dark:text-blue-300">
								<p class="mb-1 font-semibold">{$LL.auth.register.privacyNotice()}</p>
								<ul class="space-y-1 text-xs">
									<li>{$LL.auth.register.privacyPseudonymPlaintext()}</li>
									<li>{$LL.auth.register.privacyNameEncrypted()}</li>
								</ul>
							</div>
						</div>
					</div>

					<div>
						<div class="mb-1 flex items-center justify-between">
							<label
								for="fullName"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								{$LL.auth.register.childName()}
							</label>
							<span
								class="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200"
							>
								<svg class="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
										clip-rule="evenodd"
									/>
								</svg>
								{$LL.auth.register.encrypted()}
							</span>
						</div>
						<input
							id="fullName"
							type="text"
							bind:value={fullName}
							disabled={loading}
							placeholder={$LL.auth.register.childNamePlaceholder()}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
						<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{$LL.auth.register.childNameHint()}
						</p>
					</div>

					<div>
						<div class="mb-1 flex items-center justify-between">
							<label
								for="username"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								{$LL.auth.register.pseudonym()}
							</label>
							<span
								class="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
							>
								<svg class="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z"
										clip-rule="evenodd"
									/>
								</svg>
								{$LL.auth.register.plaintext()}
							</span>
						</div>
						<input
							id="username"
							type="text"
							bind:value={username}
							required
							disabled={loading}
							placeholder={$LL.auth.register.pseudonymPlaceholder()}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
						<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{$LL.auth.register.pseudonymHint()}
						</p>
					</div>

					<div>
						<label
							for="password"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							{$LL.common.password()}
						</label>
						<input
							id="password"
							type="password"
							bind:value={password}
							required
							disabled={loading}
							placeholder={$LL.auth.register.passwordPlaceholder()}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					<div>
						<label
							for="passwordConfirm"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							{$LL.auth.register.confirmPasswordLabel()}
						</label>
						<input
							id="passwordConfirm"
							type="password"
							bind:value={passwordConfirm}
							required
							disabled={loading}
							placeholder={$LL.auth.register.confirmPasswordPlaceholder2()}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					<!-- SIMPLIFIED: Keep Me Logged In Checkbox (same as login) -->
					<div
						class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900"
					>
						<label class="flex cursor-pointer items-start">
							<input
								type="checkbox"
								bind:checked={keepLoggedIn}
								disabled={loading}
								class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600
								       focus:ring-2 focus:ring-blue-500 focus:ring-offset-0
								       disabled:cursor-not-allowed disabled:opacity-50
								       dark:border-gray-600 dark:bg-gray-700"
							/>
							<div class="ml-3 flex-1">
								<span class="block font-medium text-gray-900 dark:text-white">
									{$LL.auth.register.keepLoggedIn()}
								</span>
								<span class="mt-1 block text-sm text-gray-600 dark:text-gray-400">
									{#if keepLoggedIn}
										{$LL.auth.register.keepLoggedIn30Days()}
									{:else}
										{$LL.auth.register.keepLoggedIn8Hours()}
									{/if}
								</span>
							</div>
						</label>
					</div>

					{#if error}
						<div
							class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
						>
							<div class="flex items-start">
								<svg
									class="mr-2 h-5 w-5 flex-shrink-0 text-red-600"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
										clip-rule="evenodd"
									/>
								</svg>
								<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
							</div>
						</div>
					{/if}

					<button
						type="submit"
						disabled={loading}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4
							   font-semibold text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
					>
						{#if loading}
							<span class="mr-2 animate-spin">⟳</span>
						{/if}
						{loading ? $LL.auth.register.creating() : $LL.auth.register.createAccount()}
					</button>

					{#if !isQRMode}
						<button
							type="button"
							onclick={resetToMagicWord}
							disabled={loading}
							class="w-full text-center text-sm text-gray-600 hover:text-gray-800
							       disabled:cursor-not-allowed disabled:opacity-50
							       dark:text-gray-400 dark:hover:text-gray-200"
						>
							{$LL.auth.register.backToMagicWord()}
						</button>
					{/if}
				</form>
			{/if}

			<p class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
				{$LL.auth.register.alreadyHaveAccount()}
				<button
					type="button"
					onclick={goToLogin}
					class="ml-1 font-semibold text-blue-600 underline hover:text-blue-500"
				>
					{$LL.auth.register.clickToLogin()}
				</button>
			</p>
		</div>
	</div>
</div>
