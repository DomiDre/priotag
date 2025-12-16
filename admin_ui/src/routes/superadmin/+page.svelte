<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { currentUser } from '$lib/auth.stores';
	import { apiService } from '$lib/api.service';
	import type { InstitutionDetailResponse } from '$lib/institution.types';
	import Building from 'virtual:icons/mdi/office-building';
	import Plus from 'virtual:icons/mdi/plus';
	import Edit from 'virtual:icons/mdi/pencil';
	import Users from 'virtual:icons/mdi/account-multiple';
	import Shield from 'virtual:icons/mdi/shield-account';
	import ArrowUp from 'virtual:icons/mdi/arrow-up-bold';
	import ArrowDown from 'virtual:icons/mdi/arrow-down-bold';
	import Download from 'virtual:icons/mdi/download';
	import Key from 'virtual:icons/mdi/key';
	import Lock from 'virtual:icons/mdi/lock';
	import forge from 'node-forge';

	let institutions = $state<InstitutionDetailResponse[]>([]);
	let isLoading = $state(true);
	let error = $state('');
	let successMessage = $state('');
	let showSuccessToast = $state(false);

	// Modal states
	let showCreateModal = $state(false);
	let showEditModal = $state(false);
	let showUsersModal = $state(false);
	let selectedInstitution = $state<InstitutionDetailResponse | null>(null);

	// Form states
	let newInstitution = $state({
		name: '',
		short_code: '',
		registration_magic_word: '',
		admin_public_key: ''
	});

	let editInstitution = $state({
		name: '',
		short_code: '',
		admin_public_key: '',
		active: true
	});

	// Users list state
	let institutionUsers = $state<
		Array<{
			id: string;
			username: string;
			email: string;
			role: string;
			institution_id: string;
			created: string;
			updated: string;
			lastSeen: string;
		}>
	>([]);
	let isLoadingUsers = $state(false);

	// Key generation state
	let isGeneratingKeys = $state(false);
	let generatedPrivateKey = $state<string | null>(null);
	let encryptPrivateKey = $state(true); // Default to encrypted for security
	let passphrase = $state('');
	let passphraseConfirm = $state('');
	let showPassphraseModal = $state(false);
	let passphraseError = $state('');

	/**
	 * Generate RSA keypair on client side
	 * Returns public key PEM and private key PEM
	 */
	async function generateRSAKeypair(): Promise<{ publicKey: string; privateKey: string }> {
		isGeneratingKeys = true;
		try {
			// Generate 2048-bit RSA keypair
			const keyPair = await window.crypto.subtle.generateKey(
				{
					name: 'RSA-OAEP',
					modulusLength: 2048,
					publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
					hash: 'SHA-256'
				},
				true, // extractable
				['encrypt', 'decrypt']
			);

			// Export public key as SPKI (PEM format)
			const publicKeyBuffer = await window.crypto.subtle.exportKey('spki', keyPair.publicKey);
			const publicKeyPem = arrayBufferToPem(publicKeyBuffer, 'PUBLIC KEY');

			// Export private key as PKCS8 (PEM format)
			const privateKeyBuffer = await window.crypto.subtle.exportKey('pkcs8', keyPair.privateKey);
			const privateKeyPem = arrayBufferToPem(privateKeyBuffer, 'PRIVATE KEY');

			return { publicKey: publicKeyPem, privateKey: privateKeyPem };
		} finally {
			isGeneratingKeys = false;
		}
	}

	/**
	 * Convert ArrayBuffer to PEM format
	 */
	function arrayBufferToPem(buffer: ArrayBuffer, type: string): string {
		const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
		const formatted = base64.match(/.{1,64}/g)?.join('\n') || base64;
		return `-----BEGIN ${type}-----\n${formatted}\n-----END ${type}-----`;
	}

	/**
	 * Encrypt a private key PEM with a passphrase using PKCS#8 encryption
	 */
	function encryptPrivateKeyWithPassphrase(privateKeyPem: string, passphrase: string): string {
		try {
			// Parse the private key PEM
			const privateKey = forge.pki.privateKeyFromPem(privateKeyPem);

			// Convert to PKCS#8 PrivateKeyInfo
			const privateKeyInfo = forge.pki.wrapRsaPrivateKey(forge.pki.privateKeyToAsn1(privateKey));

			// Encrypt the PrivateKeyInfo with AES-256-CBC
			// This matches what node-forge expects when decrypting in crypto.service.ts
			const encryptedPrivateKeyInfo = forge.pki.encryptPrivateKeyInfo(privateKeyInfo, passphrase, {
				algorithm: 'aes256', // AES-256-CBC
				count: 10000, // PBKDF2 iteration count
				saltSize: 16 // Salt size in bytes
			});

			// Convert to PEM format
			const encryptedPem = forge.pki.encryptedPrivateKeyToPem(encryptedPrivateKeyInfo);

			return encryptedPem;
		} catch (err) {
			console.error('Failed to encrypt private key:', err);
			throw new Error('Failed to encrypt private key with passphrase');
		}
	}

	/**
	 * Download a text file
	 */
	function downloadTextFile(content: string, filename: string) {
		const blob = new Blob([content], { type: 'text/plain' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	onMount(async () => {
		// Check if user is super admin
		if (!$currentUser.isSuperAdmin) {
			await goto('/dashboard');
			return;
		}

		await fetchInstitutions();
	});

	async function fetchInstitutions() {
		isLoading = true;
		error = '';

		try {
			institutions = await apiService.listAllInstitutions();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error loading institutions';
		} finally {
			isLoading = false;
		}
	}

	function openCreateModal() {
		newInstitution = {
			name: '',
			short_code: '',
			registration_magic_word: '',
			admin_public_key: ''
		};
		generatedPrivateKey = null;
		encryptPrivateKey = true; // Default to encrypted
		passphrase = '';
		passphraseConfirm = '';
		showCreateModal = true;
	}

	function openEditModal(institution: InstitutionDetailResponse) {
		selectedInstitution = institution;
		editInstitution = {
			name: institution.name,
			short_code: institution.short_code,
			admin_public_key: institution.admin_public_key || '',
			active: institution.active
		};
		showEditModal = true;
	}

	async function openUsersModal(institution: InstitutionDetailResponse) {
		selectedInstitution = institution;
		showUsersModal = true;
		isLoadingUsers = true;

		try {
			institutionUsers = await apiService.listInstitutionUsers(institution.id);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error loading users';
		} finally {
			isLoadingUsers = false;
		}
	}

	async function handleGenerateKeys() {
		try {
			const { publicKey, privateKey } = await generateRSAKeypair();
			newInstitution.admin_public_key = publicKey;
			generatedPrivateKey = privateKey;
			showSuccessMessage('Keys generated successfully!');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error generating keys';
		}
	}

	async function confirmPassphraseAndDownload() {
		if (!generatedPrivateKey || !newInstitution.short_code) return;

		// Validate passphrase
		if (!passphrase || passphrase.length < 8) {
			passphraseError = 'Passphrase must be at least 8 characters long';
			return;
		}

		if (passphrase !== passphraseConfirm) {
			passphraseError = 'Passphrases do not match';
			return;
		}

		try {
			// Encrypt the private key
			const encryptedPrivateKey = encryptPrivateKeyWithPassphrase(generatedPrivateKey, passphrase);

			// Download encrypted key
			downloadTextFile(
				encryptedPrivateKey,
				`${newInstitution.short_code}_private_key_encrypted.pem`
			);

			showSuccessMessage('Encrypted private key downloaded successfully');

			// Close passphrase modal
			showPassphraseModal = false;
			passphraseError = '';

			// If this was called from the create institution flow, complete it now
			if (showCreateModal) {
				await completeInstitutionCreation();
			} else {
				// If manual download, clear passphrases
				passphrase = '';
				passphraseConfirm = '';
			}
		} catch (err) {
			passphraseError = err instanceof Error ? err.message : 'Failed to encrypt private key';
		}
	}

	function cancelPassphraseModal() {
		showPassphraseModal = false;
		passphrase = '';
		passphraseConfirm = '';
		passphraseError = '';
	}

	/**
	 * Complete institution creation flow after passphrase entry
	 */
	async function completeInstitutionCreation() {
		// Close create modal
		showCreateModal = false;

		// Clear state
		generatedPrivateKey = null;
		passphrase = '';
		passphraseConfirm = '';

		// Show success message
		showSuccessMessage(
			`Institution created successfully! Encrypted private key has been downloaded.`
		);

		// Refresh institutions list
		await fetchInstitutions();
	}

	async function handleCreateInstitution() {
		// Validate that keys were generated
		if (!newInstitution.admin_public_key) {
			error = 'Please generate keys before creating the institution';
			return;
		}

		try {
			await apiService.createInstitution(newInstitution);

			// Automatically download private key
			if (generatedPrivateKey) {
				if (encryptPrivateKey) {
					// If encryption is enabled but passphrase not set, prompt for it
					if (!passphrase) {
						showPassphraseModal = true;
						passphraseError = '';
						// Don't close modal yet - wait for passphrase
						return;
					}

					// Encrypt and download
					const encryptedPrivateKey = encryptPrivateKeyWithPassphrase(
						generatedPrivateKey,
						passphrase
					);
					downloadTextFile(
						encryptedPrivateKey,
						`${newInstitution.short_code}_private_key_encrypted.pem`
					);
				} else {
					// Download unencrypted
					downloadTextFile(generatedPrivateKey, `${newInstitution.short_code}_private_key.pem`);
				}
			}

			showSuccessMessage(
				`Institution created successfully! ${encryptPrivateKey ? 'Encrypted' : ''} Private key has been downloaded.`
			);
			showCreateModal = false;
			generatedPrivateKey = null;
			passphrase = '';
			passphraseConfirm = '';
			await fetchInstitutions();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error creating institution';
		}
	}

	async function handleUpdateInstitution() {
		if (!selectedInstitution) return;

		try {
			await apiService.updateInstitution(selectedInstitution.id, editInstitution);
			showSuccessMessage('Institution updated successfully');
			showEditModal = false;
			await fetchInstitutions();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error updating institution';
		}
	}

	async function handlePromoteUser(userId: string) {
		try {
			const result = await apiService.promoteUserToInstitutionAdmin(userId);
			showSuccessMessage(result.message);
			// Refresh users list
			if (selectedInstitution) {
				institutionUsers = await apiService.listInstitutionUsers(selectedInstitution.id);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error promoting user';
		}
	}

	async function handleDemoteUser(userId: string) {
		try {
			const result = await apiService.demoteUserFromInstitutionAdmin(userId);
			showSuccessMessage(result.message);
			// Refresh users list
			if (selectedInstitution) {
				institutionUsers = await apiService.listInstitutionUsers(selectedInstitution.id);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Error demoting user';
		}
	}

	function showSuccessMessage(message: string) {
		successMessage = message;
		showSuccessToast = true;
		setTimeout(() => {
			showSuccessToast = false;
		}, 3000);
	}

	function getRoleBadgeClass(role: string) {
		switch (role) {
			case 'super_admin':
				return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
			case 'institution_admin':
				return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
			default:
				return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
		}
	}

	function formatDate(dateString: string) {
		return new Date(dateString).toLocaleDateString('de-DE', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<!-- Header -->
	<div class="border-b bg-white shadow-md dark:bg-gray-800">
		<div class="mx-auto max-w-7xl px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h1
						class="flex items-center gap-2 text-2xl font-bold text-gray-800 sm:text-3xl dark:text-white"
					>
						<Shield class="h-8 w-8 text-purple-600" />
						Super Admin Dashboard
					</h1>
					<p class="mt-1 text-xs text-gray-600 sm:text-sm dark:text-gray-300">
						Manage institutions and promote users
					</p>
				</div>
				<div class="flex gap-2">
					<button
						onclick={() => goto('/dashboard')}
						class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
					>
						Back to Dashboard
					</button>
					<button
						onclick={openCreateModal}
						class="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600"
					>
						<Plus class="h-5 w-5" />
						New Institution
					</button>
				</div>
			</div>
		</div>
	</div>

	<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
		<!-- Error Display -->
		{#if error}
			<div class="mb-4 rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
				<div class="flex items-center justify-between">
					<p class="text-sm text-red-800 dark:text-red-200">{error}</p>
					<button
						onclick={() => (error = '')}
						class="text-red-800 hover:text-red-900 dark:text-red-200 dark:hover:text-red-100"
					>
						×
					</button>
				</div>
			</div>
		{/if}

		<!-- Loading State -->
		{#if isLoading}
			<div class="flex items-center justify-center py-12">
				<div class="text-center">
					<div
						class="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-purple-200 border-t-purple-600 dark:border-purple-900 dark:border-t-purple-400"
					></div>
					<p class="text-gray-600 dark:text-gray-300">Loading institutions...</p>
				</div>
			</div>
		{:else}
			<!-- Institutions Grid -->
			<div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
				{#each institutions as institution (institution.id)}
					<div
						class="rounded-lg border bg-white p-6 shadow-sm transition-all hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
					>
						<div class="mb-4 flex items-start justify-between">
							<div class="flex items-center gap-3">
								<Building class="h-8 w-8 text-purple-600" />
								<div>
									<h3 class="font-semibold text-gray-900 dark:text-white">
										{institution.name}
									</h3>
									<p class="text-sm text-gray-500 dark:text-gray-400">
										{institution.short_code}
									</p>
								</div>
							</div>
							<span
								class="rounded-full px-2 py-1 text-xs font-medium {institution.active
									? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
									: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}"
							>
								{institution.active ? 'Active' : 'Inactive'}
							</span>
						</div>

						<div class="mb-4 space-y-2 text-sm">
							<div>
								<span class="text-gray-500 dark:text-gray-400">Magic Word:</span>
								<span class="ml-2 font-mono text-gray-900 dark:text-white">
									{institution.registration_magic_word}
								</span>
							</div>
							<div>
								<span class="text-gray-500 dark:text-gray-400">Created:</span>
								<span class="ml-2 text-gray-900 dark:text-white">
									{formatDate(institution.created)}
								</span>
							</div>
						</div>

						<div class="flex gap-2">
							<button
								onclick={() => openEditModal(institution)}
								class="flex flex-1 items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-all hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
							>
								<Edit class="h-4 w-4" />
								Edit
							</button>
							<button
								onclick={() => openUsersModal(institution)}
								class="flex flex-1 items-center justify-center gap-2 rounded-lg border border-purple-300 bg-purple-50 px-3 py-2 text-sm font-medium text-purple-700 transition-all hover:bg-purple-100 dark:border-purple-600 dark:bg-purple-900/20 dark:text-purple-300 dark:hover:bg-purple-900/30"
							>
								<Users class="h-4 w-4" />
								Users
							</button>
						</div>
					</div>
				{/each}
			</div>

			{#if institutions.length === 0}
				<div class="py-12 text-center">
					<Building class="mx-auto mb-4 h-16 w-16 text-gray-400" />
					<p class="text-gray-600 dark:text-gray-300">No institutions found</p>
					<button
						onclick={openCreateModal}
						class="mt-4 inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-purple-700"
					>
						<Plus class="h-5 w-5" />
						Create First Institution
					</button>
				</div>
			{/if}
		{/if}
	</div>
</div>

<!-- Create Institution Modal -->
{#if showCreateModal}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
		role="dialog"
		aria-modal="true"
		tabindex="-1"
		onclick={(e) => e.target === e.currentTarget && (showCreateModal = false)}
		onkeydown={(e) => e.key === 'Escape' && (showCreateModal = false)}
	>
		<div class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
			<h2 class="mb-4 text-xl font-bold text-gray-900 dark:text-white">Create New Institution</h2>

			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleCreateInstitution();
				}}
				class="space-y-4"
			>
				<div>
					<label for="inst-name" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Institution Name
					</label>
					<input
						id="inst-name"
						type="text"
						bind:value={newInstitution.name}
						required
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>

				<div>
					<label for="inst-short-code" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Short Code (uppercase, e.g. INST_001)
					</label>
					<input
						id="inst-short-code"
						type="text"
						bind:value={newInstitution.short_code}
						required
						pattern="[A-Z0-9_]+"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>

				<div>
					<label for="inst-magic-word" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Registration Magic Word
					</label>
					<input
						id="inst-magic-word"
						type="text"
						bind:value={newInstitution.registration_magic_word}
						required
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>

				<!-- RSA Keypair Generation Section -->
				<div
					class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900"
				>
					<div class="mb-3 flex items-center gap-2">
						<Key class="h-5 w-5 text-purple-600" />
						<h3 class="font-semibold text-gray-900 dark:text-white">RSA Keypair (Required)</h3>
					</div>

					{#if !generatedPrivateKey}
						<p class="mb-3 text-sm text-gray-600 dark:text-gray-400">
							Generate an RSA keypair for this institution. The private key will be automatically
							downloaded to your computer and should be given to the institution admin.
						</p>
						<button
							type="button"
							onclick={handleGenerateKeys}
							disabled={isGeneratingKeys}
							class="flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-purple-500 dark:hover:bg-purple-600"
						>
							{#if isGeneratingKeys}
								<div
									class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
								></div>
								Generating Keys...
							{:else}
								<Key class="h-4 w-4" />
								Generate RSA Keypair
							{/if}
						</button>
					{:else}
						<div class="space-y-3">
							<div
								class="flex items-center gap-2 rounded-lg bg-green-100 px-3 py-2 text-sm text-green-800 dark:bg-green-900/20 dark:text-green-300"
							>
								<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 13l4 4L19 7"
									/>
								</svg>
								Keys generated successfully!
							</div>

							<div
								class="rounded-lg border border-gray-300 bg-white p-3 dark:border-gray-600 dark:bg-gray-800"
							>
								<div class="mb-2 text-xs font-medium text-gray-700 dark:text-gray-300">
									Public Key Preview:
								</div>
								<div
									class="max-h-24 overflow-y-auto rounded bg-gray-100 p-2 font-mono text-xs text-gray-700 dark:bg-gray-900 dark:text-gray-300"
								>
									{newInstitution.admin_public_key.substring(0, 200)}...
								</div>
							</div>

							<!-- Encryption Option -->
							<div
								class="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20"
							>
								<div class="flex items-start gap-2">
									<input
										type="checkbox"
										id="encryptKey"
										bind:checked={encryptPrivateKey}
										class="mt-0.5 h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-2 focus:ring-purple-500"
									/>
									<div class="flex-1">
										<label
											for="encryptKey"
											class="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white"
										>
											<Lock class="h-4 w-4 text-purple-600" />
											Encrypt private key with passphrase (recommended)
										</label>
										<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">
											{#if encryptPrivateKey}
												You will be prompted for a passphrase when downloading the key. The
												institution admin will need this passphrase to use the key.
											{:else}
												<span class="text-orange-600 dark:text-orange-400">
													⚠️ The private key will be downloaded without encryption. Store it
													securely!
												</span>
											{/if}
										</p>
									</div>
								</div>
							</div>

							<p class="text-xs text-orange-600 dark:text-orange-400">
								⚠️ Make sure to save the private key! It will be automatically downloaded when you
								create the institution.
							</p>
						</div>
					{/if}
				</div>

				<div class="flex gap-2 pt-4">
					<button
						type="button"
						onclick={() => (showCreateModal = false)}
						class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
					>
						Cancel
					</button>
					<button
						type="submit"
						disabled={!generatedPrivateKey}
						class="flex-1 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-purple-500 dark:hover:bg-purple-600"
						title={!generatedPrivateKey ? 'Please generate keys first' : ''}
					>
						{generatedPrivateKey ? 'Create Institution & Download Key' : 'Create Institution'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Edit Institution Modal -->
{#if showEditModal && selectedInstitution}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
		role="dialog"
		aria-modal="true"
		tabindex="-1"
		onclick={(e) => e.target === e.currentTarget && (showEditModal = false)}
		onkeydown={(e) => e.key === 'Escape' && (showEditModal = false)}
	>
		<div class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
			<h2 class="mb-4 text-xl font-bold text-gray-900 dark:text-white">Edit Institution</h2>

			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleUpdateInstitution();
				}}
				class="space-y-4"
			>
				<div>
					<label for="edit-inst-name" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Institution Name
					</label>
					<input
						id="edit-inst-name"
						type="text"
						bind:value={editInstitution.name}
						required
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>

				<div>
					<label for="edit-inst-short-code" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Short Code
					</label>
					<input
						id="edit-inst-short-code"
						type="text"
						bind:value={editInstitution.short_code}
						required
						pattern="[A-Z0-9_]+"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>

				<div>
					<label for="edit-inst-public-key" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Admin Public Key
					</label>
					<textarea
						id="edit-inst-public-key"
						bind:value={editInstitution.admin_public_key}
						rows="3"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					></textarea>
				</div>

				<div class="flex items-center gap-2">
					<input
						type="checkbox"
						id="active"
						bind:checked={editInstitution.active}
						class="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-2 focus:ring-purple-500"
					/>
					<label for="active" class="text-sm font-medium text-gray-700 dark:text-gray-300">
						Active
					</label>
				</div>

				<div class="flex gap-2 pt-4">
					<button
						type="button"
						onclick={() => (showEditModal = false)}
						class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
					>
						Cancel
					</button>
					<button
						type="submit"
						class="flex-1 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600"
					>
						Update Institution
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Users Modal -->
{#if showUsersModal && selectedInstitution}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
		role="dialog"
		aria-modal="true"
		tabindex="-1"
		onclick={(e) => e.target === e.currentTarget && (showUsersModal = false)}
		onkeydown={(e) => e.key === 'Escape' && (showUsersModal = false)}
	>
		<div class="w-full max-w-4xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
			<h2 class="mb-4 text-xl font-bold text-gray-900 dark:text-white">
				Users - {selectedInstitution.name}
			</h2>

			{#if isLoadingUsers}
				<div class="py-8 text-center">
					<div
						class="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-purple-200 border-t-purple-600"
					></div>
					<p class="text-gray-600 dark:text-gray-300">Loading users...</p>
				</div>
			{:else if institutionUsers.length === 0}
				<div class="py-8 text-center">
					<Users class="mx-auto mb-4 h-12 w-12 text-gray-400" />
					<p class="text-gray-600 dark:text-gray-300">No users found in this institution</p>
				</div>
			{:else}
				<div class="max-h-96 overflow-y-auto">
					<table class="w-full">
						<thead class="border-b bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
							<tr>
								<th
									class="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300"
								>
									Username
								</th>
								<th
									class="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300"
								>
									Email
								</th>
								<th
									class="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300"
								>
									Role
								</th>
								<th
									class="px-4 py-3 text-right text-sm font-medium text-gray-700 dark:text-gray-300"
								>
									Actions
								</th>
							</tr>
						</thead>
						<tbody class="divide-y dark:divide-gray-700">
							{#each institutionUsers as user (user.id)}
								<tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
									<td class="px-4 py-3 text-sm text-gray-900 dark:text-white">
										{user.username}
									</td>
									<td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
										{user.email || '-'}
									</td>
									<td class="px-4 py-3">
										<span
											class="inline-flex rounded-full px-2 py-1 text-xs font-medium {getRoleBadgeClass(
												user.role
											)}"
										>
											{user.role === 'institution_admin' ? 'Institution Admin' : 'User'}
										</span>
									</td>
									<td class="px-4 py-3 text-right">
										{#if user.role === 'institution_admin'}
											<button
												onclick={() => handleDemoteUser(user.id)}
												class="inline-flex items-center gap-1 rounded-lg bg-orange-100 px-3 py-1 text-xs font-medium text-orange-800 transition-all hover:bg-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:hover:bg-orange-900/30"
											>
												<ArrowDown class="h-3 w-3" />
												Demote
											</button>
										{:else if user.role === 'user'}
											<button
												onclick={() => handlePromoteUser(user.id)}
												class="inline-flex items-center gap-1 rounded-lg bg-green-100 px-3 py-1 text-xs font-medium text-green-800 transition-all hover:bg-green-200 dark:bg-green-900/20 dark:text-green-300 dark:hover:bg-green-900/30"
											>
												<ArrowUp class="h-3 w-3" />
												Promote to Admin
											</button>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}

			<div class="mt-6 flex justify-end">
				<button
					onclick={() => (showUsersModal = false)}
					class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
				>
					Close
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Passphrase Modal -->
{#if showPassphraseModal}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4"
		role="dialog"
		aria-modal="true"
		tabindex="-1"
		onclick={(e) => e.target === e.currentTarget && cancelPassphraseModal()}
		onkeydown={(e) => e.key === 'Escape' && cancelPassphraseModal()}
	>
		<div class="w-full max-w-md rounded-lg bg-white p-6 shadow-2xl dark:bg-gray-800">
			<div class="mb-4 flex items-center gap-3">
				<div class="rounded-full bg-purple-100 p-3 dark:bg-purple-900/30">
					<Lock class="h-6 w-6 text-purple-600 dark:text-purple-400" />
				</div>
				<div>
					<h2 class="text-xl font-bold text-gray-900 dark:text-white">Encrypt Private Key</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Set a passphrase to protect the private key
					</p>
				</div>
			</div>

			<form
				onsubmit={(e) => {
					e.preventDefault();
					confirmPassphraseAndDownload();
				}}
				class="space-y-4"
			>
				<div>
					<label for="passphrase" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Passphrase
					</label>
					<input
						id="passphrase"
						type="password"
						bind:value={passphrase}
						required
						minlength="8"
						autocomplete="new-password"
						placeholder="Minimum 8 characters"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>

				<div>
					<label for="passphrase-confirm" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Confirm Passphrase
					</label>
					<input
						id="passphrase-confirm"
						type="password"
						bind:value={passphraseConfirm}
						required
						minlength="8"
						autocomplete="new-password"
						placeholder="Re-enter passphrase"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>

				{#if passphraseError}
					<div class="rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
						<p class="text-sm text-red-800 dark:text-red-200">{passphraseError}</p>
					</div>
				{/if}

				<div
					class="rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20"
				>
					<p class="text-xs text-yellow-800 dark:text-yellow-200">
						⚠️ <strong>Important:</strong> The institution admin will need this passphrase to use the
						private key. Make sure to communicate it securely!
					</p>
				</div>

				<div class="flex gap-2 pt-2">
					<button
						type="button"
						onclick={cancelPassphraseModal}
						class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
					>
						Cancel
					</button>
					<button
						type="submit"
						class="flex-1 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600"
					>
						Encrypt & Download
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Success Toast -->
{#if showSuccessToast}
	<div
		class="fixed right-6 bottom-6 z-50 flex items-center gap-3 rounded-lg bg-green-600 px-6 py-4 text-white shadow-2xl dark:bg-green-500"
	>
		<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
		</svg>
		<span class="font-medium">{successMessage}</span>
	</div>
{/if}
