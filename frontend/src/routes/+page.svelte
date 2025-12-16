<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/auth.store';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { LL } from '$i18n/i18n-svelte';
	import { apiService } from '$lib/api.service';

	function goToLogin() {
		goto('/login');
	}

	function goToRegisterInfo() {
		goto('/register-info');
	}

	function goToPriorities() {
		goto('/priorities');
	}

	async function doLogout() {
		try {
			await apiService.logout();
		} catch (err) {
			console.error('Logout error:', err);
		}
	}

	function scrollToFeatures() {
		document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<!-- Navigation -->
	<nav class="container mx-auto px-4 py-6">
		<div class="flex items-center justify-between">
			<div class="flex items-center space-x-2">
				<span class="text-2xl">🔐</span>
				<h1 class="text-2xl font-bold text-gray-800 dark:text-white">{$LL.app.title()}</h1>
			</div>
			<div class="flex items-center space-x-4">
				<LanguageSwitcher />

				{#if !$isAuthenticated}
					<button
						onclick={goToLogin}
						class="rounded-lg bg-gray-200 px-4 py-2 font-medium text-gray-800
								transition-colors hover:bg-gray-300 dark:bg-gray-700 dark:text-white
								dark:hover:bg-gray-600"
					>
						{$LL.landing.hero.loginButton()}
					</button>
				{:else}
					<button
						onclick={doLogout}
						class="rounded-lg bg-gray-200 px-4 py-2 font-medium text-gray-800
								transition-colors hover:bg-gray-300 dark:bg-gray-700 dark:text-white
								dark:hover:bg-gray-600"
					>
						{$LL.landing.hero.logoutButton()}
					</button>
				{/if}
			</div>
		</div>
	</nav>

	<!-- Hero Section -->
	<section class="container mx-auto max-w-6xl px-4 py-16 md:py-24">
		<div class="text-center">
			<div class="mb-8 flex justify-center">
				<div
					class="flex h-32 w-32 items-center justify-center rounded-full bg-gradient-to-br
							from-purple-500 to-blue-500 shadow-2xl"
				>
					<span class="text-7xl">📋</span>
				</div>
			</div>
			<h2 class="mb-6 text-5xl font-extrabold text-gray-900 md:text-6xl dark:text-white">
				{$LL.landing.hero.title()}
			</h2>
			<p class="mb-10 text-xl text-gray-600 md:text-2xl dark:text-gray-300">
				{$LL.landing.hero.subtitle()}
			</p>
			<div class="flex flex-col items-center justify-center gap-4 sm:flex-row">
				{#if !$isAuthenticated}
					<button
						onclick={goToLogin}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600
							px-8 py-4 text-lg font-semibold text-white shadow-xl transition
							hover:scale-105 sm:w-auto"
					>
						{$LL.landing.hero.loginButton()}
					</button>
					<button
						onclick={goToRegisterInfo}
						class="w-full rounded-xl bg-white px-8 py-4 text-lg font-semibold text-gray-800
							shadow-lg transition-colors hover:bg-gray-100
							sm:w-auto dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700"
					>
						{$LL.landing.hero.registerButton()}
					</button>
				{:else}
					<button
						onclick={goToPriorities}
						class="w-full rounded-xl bg-white px-8 py-4 text-lg font-semibold text-gray-800
							shadow-lg transition-colors hover:bg-gray-100
							sm:w-auto dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700"
					>
						{$LL.landing.hero.prioritiesButton()}
					</button>
				{/if}
				<button
					onclick={scrollToFeatures}
					class="w-full rounded-xl border-2 border-purple-600 px-8 py-4 text-lg
							font-semibold text-purple-600 transition-colors hover:bg-purple-50
							sm:w-auto dark:border-purple-400 dark:text-purple-400
							dark:hover:bg-purple-900/20"
				>
					{$LL.landing.hero.learnMore()}
				</button>
			</div>
		</div>
	</section>

	<!-- Features Section -->
	<section id="features" class="bg-white py-20 dark:bg-gray-900">
		<div class="container mx-auto max-w-6xl px-4">
			<div class="mb-16 text-center">
				<h3 class="mb-4 text-4xl font-bold text-gray-900 dark:text-white">
					{$LL.landing.features.title()}
				</h3>
				<p class="text-xl text-gray-600 dark:text-gray-300">
					{$LL.landing.features.subtitle()}
				</p>
			</div>

			<div class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
				<!-- Privacy First -->
				<div
					class="rounded-2xl bg-gradient-to-br from-purple-50 to-purple-100 p-6
							dark:from-purple-900/20 dark:to-purple-800/20"
				>
					<div class="mb-4 text-5xl">🔒</div>
					<h4 class="mb-3 text-xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.features.privacy.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.features.privacy.description()}
					</p>
				</div>

				<!-- GDPR Compliant -->
				<div
					class="rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 p-6
							dark:from-blue-900/20 dark:to-blue-800/20"
				>
					<div class="mb-4 text-5xl">✅</div>
					<h4 class="mb-3 text-xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.features.gdpr.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.features.gdpr.description()}
					</p>
				</div>

				<!-- Easy to Use -->
				<div
					class="rounded-2xl bg-gradient-to-br from-green-50 to-green-100 p-6
							dark:from-green-900/20 dark:to-green-800/20"
				>
					<div class="mb-4 text-5xl">🎯</div>
					<h4 class="mb-3 text-xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.features.easyToUse.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.features.easyToUse.description()}
					</p>
				</div>

				<!-- Multi-Institution -->
				<div
					class="rounded-2xl bg-gradient-to-br from-yellow-50 to-yellow-100 p-6
							dark:from-yellow-900/20 dark:to-yellow-800/20"
				>
					<div class="mb-4 text-5xl">🏢</div>
					<h4 class="mb-3 text-xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.features.multiInstitution.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.features.multiInstitution.description()}
					</p>
				</div>

				<!-- Secure & Reliable -->
				<div
					class="rounded-2xl bg-gradient-to-br from-red-50 to-red-100 p-6
							dark:from-red-900/20 dark:to-red-800/20"
				>
					<div class="mb-4 text-5xl">🛡️</div>
					<h4 class="mb-3 text-xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.features.secure.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.features.secure.description()}
					</p>
				</div>

				<!-- Open Source -->
				<div
					class="rounded-2xl bg-gradient-to-br from-indigo-50 to-indigo-100 p-6
							dark:from-indigo-900/20 dark:to-indigo-800/20"
				>
					<div class="mb-4 text-5xl">💻</div>
					<h4 class="mb-3 text-xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.features.transparent.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.features.transparent.description()}
					</p>
				</div>
			</div>
		</div>
	</section>

	<!-- How It Works Section -->
	<section
		class="bg-gradient-to-br from-purple-50 to-blue-50 py-20 dark:from-gray-800 dark:to-gray-900"
	>
		<div class="container mx-auto max-w-6xl px-4">
			<div class="mb-16 text-center">
				<h3 class="mb-4 text-4xl font-bold text-gray-900 dark:text-white">
					{$LL.landing.howItWorks.title()}
				</h3>
				<p class="text-xl text-gray-600 dark:text-gray-300">
					{$LL.landing.howItWorks.subtitle()}
				</p>
			</div>

			<div class="grid gap-8 md:grid-cols-3">
				<!-- Step 1 -->
				<div class="text-center">
					<div
						class="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full
								bg-gradient-to-br from-purple-600 to-blue-600 text-4xl font-bold
								text-white shadow-xl"
					>
						1
					</div>
					<h4 class="mb-3 text-2xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.howItWorks.step1.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.howItWorks.step1.description()}
					</p>
				</div>

				<!-- Step 2 -->
				<div class="text-center">
					<div
						class="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full
								bg-gradient-to-br from-purple-600 to-blue-600 text-4xl font-bold
								text-white shadow-xl"
					>
						2
					</div>
					<h4 class="mb-3 text-2xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.howItWorks.step2.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.howItWorks.step2.description()}
					</p>
				</div>

				<!-- Step 3 -->
				<div class="text-center">
					<div
						class="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full
								bg-gradient-to-br from-purple-600 to-blue-600 text-4xl font-bold
								text-white shadow-xl"
					>
						3
					</div>
					<h4 class="mb-3 text-2xl font-bold text-gray-900 dark:text-white">
						{$LL.landing.howItWorks.step3.title()}
					</h4>
					<p class="text-gray-700 dark:text-gray-300">
						{$LL.landing.howItWorks.step3.description()}
					</p>
				</div>
			</div>
		</div>
	</section>

	<!-- CTA Section -->
	{#if !$isAuthenticated}
		<section class="bg-gradient-to-r from-purple-600 to-blue-600 py-20">
			<div class="container mx-auto max-w-4xl px-4 text-center">
				<h3 class="mb-4 text-4xl font-bold text-white">
					{$LL.landing.cta.title()}
				</h3>
				<p class="mb-8 text-xl text-purple-100">
					{$LL.landing.cta.subtitle()}
				</p>
				<div class="flex flex-col items-center justify-center gap-4 sm:flex-row">
					<button
						onclick={goToLogin}
						class="w-full transform rounded-xl bg-white px-8 py-4 text-lg font-semibold
								text-purple-600 shadow-xl transition hover:scale-105 sm:w-auto"
					>
						{$LL.landing.cta.loginButton()}
					</button>
					<button
						onclick={goToRegisterInfo}
						class="w-full rounded-xl border-2 border-white px-8 py-4 text-lg font-semibold
								text-white transition-colors hover:bg-white/10 sm:w-auto"
					>
						{$LL.landing.cta.registerInfo()}
					</button>
				</div>
			</div>
		</section>
	{/if}

	<!-- Footer -->
	<footer class="bg-gray-900 py-12 text-gray-300">
		<div class="container mx-auto max-w-6xl px-4">
			<div class="grid gap-8 md:grid-cols-3">
				<!-- About -->
				<div>
					<div class="mb-4 flex items-center space-x-2">
						<span class="text-2xl">🔐</span>
						<h4 class="text-xl font-bold text-white">{$LL.app.title()}</h4>
					</div>
					<p class="text-sm text-gray-400">
						{$LL.landing.footer.description()}
					</p>
				</div>

				<!-- Links -->
				<div>
					<h5 class="mb-4 font-bold text-white">{$LL.landing.footer.links()}</h5>
					<ul class="space-y-2 text-sm">
						<li>
							<a
								href="https://github.com/domidre/priotag"
								target="_blank"
								rel="noopener noreferrer"
								class="transition-colors hover:text-white"
							>
								{$LL.common.github()}
							</a>
						</li>
						<li>
							<button onclick={goToLogin} class="transition-colors hover:text-white">
								{$LL.auth.login.title()}
							</button>
						</li>
						<li>
							<button onclick={goToRegisterInfo} class="transition-colors hover:text-white">
								{$LL.auth.register.title()}
							</button>
						</li>
					</ul>
				</div>

				<!-- Legal -->
				<div>
					<h5 class="mb-4 font-bold text-white">{$LL.landing.footer.legal()}</h5>
					<ul class="space-y-2 text-sm">
						<li>
							<a href="/privacy" class="transition-colors hover:text-white">
								{$LL.common.privacy()}
							</a>
						</li>
						<li>
							<a href="/imprint" class="transition-colors hover:text-white">
								{$LL.common.imprint()}
							</a>
						</li>
					</ul>
				</div>
			</div>

			<div class="mt-8 border-t border-gray-800 pt-8 text-center text-sm text-gray-500">
				© {new Date().getFullYear()}
				{$LL.app.title()} - Open Source Software
			</div>
		</div>
	</footer>
</div>
