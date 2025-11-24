<script lang="ts">
	import Plus from 'virtual:icons/mdi/plus';
	import Download from 'virtual:icons/mdi/download';
	import Calendar from 'virtual:icons/mdi/calendar';
	import QrCode from 'virtual:icons/mdi/qrcode';
	import type { Stats } from '$lib/dashboard.types';

	interface Props {
		keyUploaded: boolean;
		stats: Stats;
		decryptedUsersCount: number;
		onManualEntry: () => void;
		onExportExcel: () => void;
		onManageVacationDays: () => void;
		onGenerateQR: () => void;
	}

	let {
		keyUploaded,
		stats,
		decryptedUsersCount,
		onManualEntry,
		onExportExcel,
		onManageVacationDays,
		onGenerateQR
	}: Props = $props();
</script>

<div class="space-y-6">
	<!-- Quick Actions -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
	>
		<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h3>
		<div class="space-y-3">
			<button
				type="button"
				class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105"
				onclick={onGenerateQR}
			>
				<QrCode class="h-5 w-5" />
				QR-Code Erstellen
			</button>

			<button
				type="button"
				class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105"
				onclick={onManualEntry}
			>
				<Plus class="h-5 w-5" />
				Manuelle Eingabe
			</button>

			<button
				type="button"
				class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-orange-600 to-red-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105"
				onclick={onManageVacationDays}
			>
				<Calendar class="h-5 w-5" />
				Abwesenheitstage
			</button>

			<button
				type="button"
				class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
				onclick={onExportExcel}
				disabled={!keyUploaded || stats.totalUsers === 0}
			>
				<Download class="h-5 w-5" />
				Excel Export
			</button>
		</div>

		{#if !keyUploaded}
			<div
				class="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20"
			>
				<p class="text-xs text-yellow-800 dark:text-yellow-400">
					Privaten Schlüssel hochladen um Export zu erlauben
				</p>
			</div>
		{/if}
	</div>

	<!-- Monthly Overview -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
	>
		<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Monatliche Übersicht</h3>
		<div class="space-y-4">
			<div>
				<div class="mb-2 flex justify-between text-sm">
					<span class="text-gray-600 dark:text-gray-300">Vervollständigungs Fortschritt</span>
					<span class="font-medium text-gray-900 dark:text-white">{stats.submissionRate}%</span>
				</div>
				<div class="h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-2.5 rounded-full bg-gradient-to-r from-purple-500 to-blue-600 transition-all duration-500"
						style="width: {stats.submissionRate}%"
					></div>
				</div>
			</div>

			<div class="border-t border-gray-200 pt-4 dark:border-gray-700">
				<div class="mb-2 flex items-center justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-300">Nutzer Einreichungen</span>
					<span class="text-sm font-medium text-gray-900 dark:text-white">{stats.submitted}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-300">Manuelle Einträge</span>
					<span class="text-sm font-medium text-gray-900 dark:text-white">0</span>
				</div>
				{#if keyUploaded}
					<div
						class="mt-2 flex items-center justify-between border-t border-gray-200 pt-2 dark:border-gray-700"
					>
						<span class="text-sm text-gray-600 dark:text-gray-300">Entschlüsselt</span>
						<span class="text-sm font-medium text-purple-600 dark:text-purple-400"
							>{decryptedUsersCount}</span
						>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
