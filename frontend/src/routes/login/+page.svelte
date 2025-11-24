<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/auth.store';
	import { apiService } from '$lib/api.service';
	import { onMount } from 'svelte';
	import Loading from '$lib/components/Loading.svelte';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { LL } from '$i18n/i18n-svelte';

	let username = '';
	let password = '';
	let keepLoggedIn = false;
	let error = '';
	let isLoading = false;

	onMount(() => {
		if ($isAuthenticated) {
			goto('/priorities');
		}
	});

	async function handleLogin() {
		error = '';
		isLoading = true;

		try {
			await apiService.login(username, password, keepLoggedIn);
			goto('/priorities');
		} catch (err) {
			error = (err as Error).message;
		} finally {
			isLoading = false;
		}
	}

	function goToRegister() {
		goto('/register-info');
	}
</script>

{#if $isAuthenticated}
	<Loading message={$LL.common.loading()} />
{:else}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-5xl px-4 py-8">
			<!-- Language Switcher -->
			<div class="mb-4 flex justify-end">
				<LanguageSwitcher />
			</div>

			<!-- Header -->
			<div class="mb-8 text-center">
				<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">{$LL.app.title()}</h1>
				<p class="text-gray-600 dark:text-gray-300">{$LL.app.subtitle()}</p>
			</div>

			<!-- Main Card -->
			<div class="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
				<form class="space-y-6" on:submit|preventDefault={handleLogin}>
					<!-- Username -->
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$LL.common.username()}
						<input
							type="text"
							bind:value={username}
							required
							disabled={isLoading}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</label>

					<!-- Password -->
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$LL.common.password()}
						<input
							type="password"
							bind:value={password}
							required
							disabled={isLoading}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</label>

					<!-- Keep Me Logged In Checkbox -->
					<div
						class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900"
					>
						<label class="flex cursor-pointer items-start">
							<input
								type="checkbox"
								bind:checked={keepLoggedIn}
								disabled={isLoading}
								class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600
								       focus:ring-2 focus:ring-blue-500 focus:ring-offset-0
								       disabled:cursor-not-allowed disabled:opacity-50
								       dark:border-gray-600 dark:bg-gray-700"
							/>
							<div class="ml-3 flex-1">
								<span class="block font-medium text-gray-900 dark:text-white">
									{$LL.auth.login.keepLoggedIn()}
								</span>
								<span class="mt-1 block text-sm text-gray-600 dark:text-gray-400">
									{#if keepLoggedIn}
										{$LL.auth.login.keepLoggedInDesc30Days()}
									{:else}
										{$LL.auth.login.keepLoggedInDesc8Hours()}
									{/if}
								</span>
							</div>
						</label>
					</div>

					<!-- Login Button -->
					<button
						type="submit"
						disabled={isLoading}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold
							   text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
					>
						{isLoading ? $LL.auth.login.loggingIn() : $LL.auth.login.loginButton()}
					</button>

					<!-- Register Button -->
					<button
						type="button"
						disabled={isLoading}
						class="w-full rounded-xl bg-gray-600 py-3 font-semibold text-white shadow-lg
						       transition-colors hover:bg-gray-700
						       disabled:cursor-not-allowed disabled:opacity-50"
						on:click={goToRegister}
					>
						{$LL.auth.login.registerButton()}
					</button>

					<!-- Error Message -->
					{#if error}
						<div
							class="mt-4 rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
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
								<span>{error}</span>
							</div>
						</div>
					{/if}
				</form>

				<!-- Security Note -->
				<div class="mt-6 border-t border-gray-200 pt-6 dark:border-gray-700">
					<div class="flex items-start text-xs text-gray-500 dark:text-gray-400">
						<svg
							class="mr-2 h-4 w-4 flex-shrink-0 text-green-600"
							fill="currentColor"
							viewBox="0 0 20 20"
						>
							<path
								fill-rule="evenodd"
								d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
								clip-rule="evenodd"
							/>
						</svg>
						<p class="leading-relaxed">
							{$LL.auth.login.securityNote()}
						</p>
					</div>
				</div>
			</div>

			<!-- Footer -->
			<div class="mt-8 text-center">
				<div class="flex flex-wrap justify-center gap-4 text-sm text-gray-600 dark:text-gray-400">
					<a
						href="https://github.com/domidre/priotag"
						target="_blank"
						rel="noopener noreferrer"
						class="transition-colors hover:text-blue-600 dark:hover:text-blue-400"
					>
						{$LL.common.github()}
					</a>
					<span class="text-gray-400">•</span>
					<a href="/imprint" class="transition-colors hover:text-blue-600 dark:hover:text-blue-400">
						{$LL.common.imprint()}
					</a>
					<span class="text-gray-400">•</span>
					<a href="/privacy" class="transition-colors hover:text-blue-600 dark:hover:text-blue-400">
						{$LL.common.privacy()}
					</a>
				</div>
			</div>
		</div>
	</div>
{/if}
