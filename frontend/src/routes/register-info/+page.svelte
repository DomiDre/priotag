<!-- src/routes/register-info/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { LL } from '$i18n/i18n-svelte';

	function goToLogin() {
		goto('/login');
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
				{$LL.auth.register.infoTitle()}
			</h1>
		</div>

		<!-- Main Card -->
		<div class="mx-auto max-w-2xl rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-800">
			<div class="mb-6 text-center">
				<div
					class="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500"
				>
					<span class="text-5xl">🔐</span>
				</div>
				<h2 class="mb-4 text-2xl font-bold text-gray-800 dark:text-white">
					{$LL.auth.register.infoHeading()}
				</h2>
				<p class="text-lg text-gray-600 dark:text-gray-300">
					{$LL.auth.register.infoDescription()}
				</p>
			</div>

			<!-- Registration Methods -->
			<div class="my-8">
				<h3 class="mb-4 text-lg font-semibold text-gray-800 dark:text-white">
					{$LL.auth.register.infoStepsTitle()}
				</h3>

				<div class="space-y-4">
					<!-- QR Code Method -->
					<div
						class="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20"
					>
						<div class="flex items-start">
							<div class="mr-4 flex-shrink-0 text-3xl">📱</div>
							<div>
								<h4 class="mb-1 font-semibold text-blue-900 dark:text-blue-100">
									{$LL.auth.register.infoStep1Title()}
								</h4>
								<p class="text-sm text-blue-800 dark:text-blue-200">
									{$LL.auth.register.infoStep1Description()}
								</p>
							</div>
						</div>
					</div>

					<!-- Registration Link Method -->
					<div
						class="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20"
					>
						<div class="flex items-start">
							<div class="mr-4 flex-shrink-0 text-3xl">🔗</div>
							<div>
								<h4 class="mb-1 font-semibold text-green-900 dark:text-green-100">
									{$LL.auth.register.infoStep2Title()}
								</h4>
								<p class="text-sm text-green-800 dark:text-green-200">
									{$LL.auth.register.infoStep2Description()}
								</p>
							</div>
						</div>
					</div>

					<!-- Contact Admin Method -->
					<div
						class="rounded-lg border border-purple-200 bg-purple-50 p-4 dark:border-purple-800 dark:bg-purple-900/20"
					>
						<div class="flex items-start">
							<div class="mr-4 flex-shrink-0 text-3xl">👤</div>
							<div>
								<h4 class="mb-1 font-semibold text-purple-900 dark:text-purple-100">
									{$LL.auth.register.infoStep3Title()}
								</h4>
								<p class="text-sm text-purple-800 dark:text-purple-200">
									{$LL.auth.register.infoStep3Description()}
								</p>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Why Section -->
			<div
				class="my-6 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900"
			>
				<div class="flex items-start">
					<svg
						class="mr-2 h-5 w-5 flex-shrink-0 text-gray-600 dark:text-gray-400"
						fill="currentColor"
						viewBox="0 0 20 20"
					>
						<path
							fill-rule="evenodd"
							d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
							clip-rule="evenodd"
						/>
					</svg>
					<div>
						<h4 class="mb-1 font-semibold text-gray-800 dark:text-gray-200">
							{$LL.auth.register.infoWhyTitle()}
						</h4>
						<p class="text-sm text-gray-600 dark:text-gray-400">
							{$LL.auth.register.infoWhyDescription()}
						</p>
					</div>
				</div>
			</div>

			<!-- Back to Login Button -->
			<button
				type="button"
				onclick={goToLogin}
				class="w-full rounded-xl bg-gray-600 py-3 font-semibold text-white shadow-lg
				       transition-colors hover:bg-gray-700"
			>
				{$LL.auth.register.infoBackToLogin()}
			</button>
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
