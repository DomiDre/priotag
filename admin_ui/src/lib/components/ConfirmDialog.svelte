<script lang="ts">
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import Close from 'virtual:icons/mdi/close';

	interface Props {
		isOpen: boolean;
		title: string;
		message: string;
		confirmText?: string;
		cancelText?: string;
		variant?: 'danger' | 'warning' | 'info';
		onConfirm: () => void | Promise<void>;
		onCancel: () => void;
	}

	let {
		isOpen = $bindable(),
		title,
		message,
		confirmText = 'Bestätigen',
		cancelText = 'Abbrechen',
		variant = 'danger',
		onConfirm,
		onCancel
	}: Props = $props();

	let isLoading = $state(false);

	async function handleConfirm() {
		isLoading = true;
		try {
			await onConfirm();
		} finally {
			isLoading = false;
		}
	}

	function handleCancel() {
		if (!isLoading) {
			onCancel();
		}
	}

	const variantClasses = {
		danger: 'bg-red-600 hover:bg-red-700 focus:ring-red-500',
		warning: 'bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500',
		info: 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
	};
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
		transition:fade={{ duration: 200 }}
		onclick={handleCancel}
		onkeydown={(e) => e.key === 'Escape' && handleCancel()}
		role="button"
		tabindex="-1"
	>
		<!-- Dialog -->
		<div
			class="relative w-full max-w-md rounded-lg bg-white shadow-2xl dark:bg-gray-800"
			transition:scale={{ duration: 200, easing: cubicOut, start: 0.95 }}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-labelledby="confirm-dialog-title"
			aria-describedby="confirm-dialog-message"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
				<h3 id="confirm-dialog-title" class="text-lg font-semibold text-gray-900 dark:text-white">
					{title}
				</h3>
				<button
					type="button"
					onclick={handleCancel}
					disabled={isLoading}
					class="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-900 disabled:opacity-50 dark:hover:bg-gray-700 dark:hover:text-white"
					aria-label="Schließen"
				>
					<Close class="h-5 w-5" />
				</button>
			</div>

			<!-- Content -->
			<div class="p-6">
				<p id="confirm-dialog-message" class="text-gray-700 dark:text-gray-300">
					{message}
				</p>
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 border-t border-gray-200 p-4 dark:border-gray-700">
				<button
					type="button"
					onclick={handleCancel}
					disabled={isLoading}
					class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-gray-200 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:ring-gray-700"
				>
					{cancelText}
				</button>
				<button
					type="button"
					onclick={handleConfirm}
					disabled={isLoading}
					class="rounded-lg px-4 py-2 text-sm font-medium text-white focus:outline-none focus:ring-4 disabled:opacity-50 {variantClasses[
						variant
					]}"
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
							Lädt...
						</span>
					{:else}
						{confirmText}
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
