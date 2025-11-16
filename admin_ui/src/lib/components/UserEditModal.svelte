<script lang="ts">
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import Close from 'virtual:icons/mdi/close';
	import { apiService } from '$lib/api.service';

	interface Props {
		isOpen: boolean;
		userId: string | null;
		userName: string;
		onClose: () => void;
		onSuccess: () => void;
	}

	let { isOpen = $bindable(), userId, userName, onClose, onSuccess }: Props = $props();

	// Form state
	let formUsername = $state('');
	let formEmail = $state('');
	let formRole: 'user' | 'admin' | 'service' | 'generic' = $state('user');

	let isLoading = $state(false);
	let isFetching = $state(false);
	let error = $state('');

	// Load user details when modal opens
	$effect(() => {
		if (isOpen && userId) {
			loadUserDetails();
		} else {
			resetForm();
		}
	});

	async function loadUserDetails() {
		if (!userId) return;

		isFetching = true;
		error = '';
		try {
			const userDetails = await apiService.getUserDetail(userId);
			formUsername = userDetails.username || '';
			formEmail = userDetails.email || '';
			formRole = userDetails.role || 'user';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Fehler beim Laden der Benutzerdaten';
			console.error('Error loading user details:', err);
		} finally {
			isFetching = false;
		}
	}

	function resetForm() {
		formUsername = '';
		formEmail = '';
		formRole = 'user';
		error = '';
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!userId) return;

		error = '';
		isLoading = true;

		try {
			await apiService.updateUser(userId, {
				username: formUsername.trim(),
				email: formEmail.trim() || undefined,
				role: formRole
			});

			onSuccess();
			onClose();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Fehler beim Aktualisieren des Benutzers';
			console.error('Error updating user:', err);
		} finally {
			isLoading = false;
		}
	}

	function handleClose() {
		if (!isLoading) {
			onClose();
		}
	}
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
		transition:fade={{ duration: 200 }}
		onclick={handleClose}
		onkeydown={(e) => e.key === 'Escape' && handleClose()}
		role="button"
		tabindex="-1"
	>
		<!-- Modal -->
		<div
			class="relative w-full max-w-md rounded-lg bg-white shadow-2xl dark:bg-gray-800"
			transition:scale={{ duration: 200, easing: cubicOut, start: 0.95 }}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-labelledby="user-edit-modal-title"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
				<h3 id="user-edit-modal-title" class="text-lg font-semibold text-gray-900 dark:text-white">
					Benutzer bearbeiten
				</h3>
				<button
					type="button"
					onclick={handleClose}
					disabled={isLoading || isFetching}
					class="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-900 disabled:opacity-50 dark:hover:bg-gray-700 dark:hover:text-white"
					aria-label="Schließen"
				>
					<Close class="h-5 w-5" />
				</button>
			</div>

			<!-- Content -->
			<form onsubmit={handleSubmit} class="p-6">
				{#if isFetching}
					<div class="flex items-center justify-center py-8">
						<svg class="h-8 w-8 animate-spin text-purple-600" viewBox="0 0 24 24">
							<circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
								fill="none"
							></circle>
							<path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							></path>
						</svg>
					</div>
				{:else}
					<div class="space-y-4">
						<!-- Username -->
						<div>
							<label for="username" class="mb-2 block text-sm font-medium text-gray-900 dark:text-white">
								Benutzername
							</label>
							<input
								id="username"
								type="text"
								bind:value={formUsername}
								required
								disabled={isLoading}
								class="block w-full rounded-lg border border-gray-300 p-2.5 text-sm text-gray-900 focus:border-purple-500 focus:ring-purple-500 disabled:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-purple-500 dark:focus:ring-purple-500"
								placeholder="Benutzername eingeben"
							/>
						</div>

						<!-- Email -->
						<div>
							<label for="email" class="mb-2 block text-sm font-medium text-gray-900 dark:text-white">
								E-Mail (optional)
							</label>
							<input
								id="email"
								type="email"
								bind:value={formEmail}
								disabled={isLoading}
								class="block w-full rounded-lg border border-gray-300 p-2.5 text-sm text-gray-900 focus:border-purple-500 focus:ring-purple-500 disabled:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-purple-500 dark:focus:ring-purple-500"
								placeholder="email@beispiel.de"
							/>
						</div>

						<!-- Role -->
						<div>
							<label for="role" class="mb-2 block text-sm font-medium text-gray-900 dark:text-white">
								Rolle
							</label>
							<select
								id="role"
								bind:value={formRole}
								disabled={isLoading}
								class="block w-full rounded-lg border border-gray-300 p-2.5 text-sm text-gray-900 focus:border-purple-500 focus:ring-purple-500 disabled:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-purple-500 dark:focus:ring-purple-500"
							>
								<option value="user">Benutzer</option>
								<option value="admin">Administrator</option>
								<option value="service">Service</option>
								<option value="generic">Generic</option>
							</select>
						</div>

						<!-- Error Message -->
						{#if error}
							<div class="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400">
								{error}
							</div>
						{/if}
					</div>
				{/if}
			</form>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 border-t border-gray-200 p-4 dark:border-gray-700">
				<button
					type="button"
					onclick={handleClose}
					disabled={isLoading || isFetching}
					class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-gray-200 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:ring-gray-700"
				>
					Abbrechen
				</button>
				<button
					type="submit"
					onclick={handleSubmit}
					disabled={isLoading || isFetching || !formUsername.trim()}
					class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 focus:outline-none focus:ring-4 focus:ring-purple-300 disabled:opacity-50 dark:focus:ring-purple-800"
				>
					{#if isLoading}
						<span class="flex items-center gap-2">
							<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24">
								<circle
									class="opacity-25"
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									stroke-width="4"
									fill="none"
								></circle>
								<path
									class="opacity-75"
									fill="currentColor"
									d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
								></path>
							</svg>
							Speichert...
						</span>
					{:else}
						Speichern
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
