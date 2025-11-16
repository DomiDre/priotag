<script lang="ts">
	import { onMount } from 'svelte';
	import { scale } from 'svelte/transition';
	import Refresh from 'virtual:icons/mdi/refresh';
	import { apiService } from '$lib/api.service';
	import { cryptoService } from '$lib/crypto.service';
	import { webAuthnCryptoService } from '$lib/webauthn-crypto.service';
	import DecryptedDataModal from '$lib/components/DecryptedDataModal.svelte';
	import StatsCards from '$lib/components/StatsCards.svelte';
	import AuthenticationPanel from '$lib/components/AuthenticationPanel.svelte';
	import PrioritiesOverview from '$lib/components/PrioritiesOverview.svelte';
	import UserSubmissionsTable from '$lib/components/UserSubmissionsTable.svelte';
	import SidebarActions from '$lib/components/SidebarActions.svelte';
	import ManualEntryModal from '$lib/components/ManualEntryModal.svelte';
	import VacationDayModal from '$lib/components/VacationDayModal.svelte';
	import ErrorDisplay from '$lib/components/ErrorDisplay.svelte';
	import LoadingIndicator from '$lib/components/LoadingIndicator.svelte';
	import UserEditModal from '$lib/components/UserEditModal.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import type { DecryptedData, UserDisplay } from '$lib/dashboard.types';
	import { dayKeys } from '$lib/priorities.config';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import type { WeekPriority } from '$lib/priorities.types';
	import type { VacationDayAdmin, VacationDayType } from '$lib/vacation-days.types';
	import { formatMonthForAPI, getMonthOptions } from '$lib/dateHelpers.utils';

	// Daten beim Laden abrufen
	onMount(() => {
		fetchTotalUsers();
		fetchUserSubmissions();
		fetchVacationDays();
		initialFetchDone = true;
	});

	// Konstanten
	const monthOptions = getMonthOptions();

	// Zustand
	let selectedMonth = $state(monthOptions[0]);
	let keyUploaded = $state(false);
	let showManualEntry = $state(false);
	let showVacationDayModal = $state(false);
	let searchQuery = $state('');
	let keyFile = $state<File | null>(null);
	let isLoading = $state(true);
	let isRefreshing = $state(false);
	let error = $state('');
	let decryptionError = $state('');
	let showOverview = $state(false);
	let authMode: 'file' | 'webauthn' | null = $state(null);
	let showSuccessToast = $state(false);
	let successMessage = $state('');

	// User/Priority management modals
	let showUserEditModal = $state(false);
	let editingUser: UserDisplay | null = $state(null);
	let showDeleteUserConfirm = $state(false);
	let deletingUser: UserDisplay | null = $state(null);
	let showDeletePriorityConfirm = $state(false);
	let deletingPriority: UserDisplay | null = $state(null);

	// Entschlüsselungszustand
	let isDecrypting = $state(false);
	let isDecryptingAll = $state(false);
	let showDecryptedModal = $state(false);
	let decryptedData = $state<DecryptedData | null>(null);
	let decryptedUsers = new SvelteMap<string, DecryptedData>();

	// Daten
	let users = $state<UserDisplay[]>([]);
	let totalRegisteredUsers = $state(0);
	let vacationDays = $state<VacationDayAdmin[]>([]);

	// Passphrase-Zustand
	let passphraseInput = $state('');
	let showPassphrasePrompt = $state(false);
	let pendingKeyFile = $state<File | null>(null);

	// Verfolgen, ob der erste Abruf abgeschlossen ist
	let initialFetchDone = $state(false);

	// Statistiken reaktiv mit $derived berechnen
	let stats = $derived.by(() => {
		const submitted = users.filter((u) => u.submitted && u.hasData && !u.isManual).length;
		const manualSubmitted = users.filter((u) => u.submitted && u.hasData && u.isManual).length;
		const pending = totalRegisteredUsers - submitted;
		const submissionRate =
			totalRegisteredUsers > 0 ? Math.round((submitted / totalRegisteredUsers) * 100) : 0;
		const sumSubmit = submitted + manualSubmitted;

		return {
			totalUsers: totalRegisteredUsers,
			submitted: sumSubmit,
			pending,
			submissionRate
		};
	});

	// Übersichtsdatenstruktur mit $derived erstellen
	let overviewData = $derived.by(() => {
		if (decryptedUsers.size === 0) return [];

		const data: any[] = [];

		decryptedUsers.forEach((userData) => {
			const weeks = userData.priorities?.weeks || [];

			data.push({
				userName: userData.userName,
				weeks: weeks.map((week: any) => ({
					weekNumber: week.weekNumber,
					priorities: dayKeys.map((day) => week[day] || null)
				}))
			});
		});

		return data.sort((a, b) => a.userName.localeCompare(b.userName));
	});

	// Alle eindeutigen Wochen über alle Benutzer hinweg abrufen
	let allWeeks = $derived.by(() => {
		const weekSet = new SvelteSet<number>();
		decryptedUsers.forEach((userData) => {
			const weeks = userData.priorities?.weeks || [];
			weeks.forEach((week: any) => {
				weekSet.add(week.weekNumber);
			});
		});
		return Array.from(weekSet).sort((a, b) => a - b);
	});

	// Benutzer basierend auf Suchanfrage mit $derived filtern
	let filteredUsers = $derived.by(() => {
		return users.filter((user) => {
			const displayName = getDisplayName(user.name);
			return displayName.toLowerCase().includes(searchQuery.toLowerCase());
		});
	});

	// Auf Monatsänderungen mit $effect reagieren
	$effect(() => {
		if (initialFetchDone && selectedMonth) {
			decryptedUsers.clear();
			showOverview = false;
			fetchUserSubmissions();
		}
	});

	// Benutzerübermittlungen von der API abrufen
	// Gesamtzahl registrierter Benutzer abrufen
	async function fetchTotalUsers() {
		try {
			const data = await apiService.getTotalUsers();
			totalRegisteredUsers = data.totalUsers;
		} catch (err) {
			console.error('Fehler beim Abrufen der Benutzerzahl:', err);
		}
	}

	async function fetchUserSubmissions() {
		isLoading = true;
		error = '';

		try {
			const apiMonth = formatMonthForAPI(selectedMonth);
			const [userSubmissions, manualEntriesData] = await Promise.all([
				apiService.getUserSubmissions(apiMonth),
				apiService.getManualSubmissions(apiMonth)
			]);

			// Reguläre Benutzerübermittlungen in Anzeigeformat transformieren
			const regularUsers = userSubmissions.map((submission: any, index: number) => ({
				id: index + 1,
				name: submission.userName,
				userId: submission.userId,
				priorityId: submission.priorityId,
				submitted: true,
				encrypted: true,
				hasData: !!submission.prioritiesEncryptedFields,
				isManual: false,
				adminWrappedDek: submission.adminWrappedDek,
				userEncryptedFields: submission.userEncryptedFields,
				prioritiesEncryptedFields: submission.prioritiesEncryptedFields
			}));

			// Manuelle Einträge in Anzeigeformat transformieren
			const manualUsers = manualEntriesData.map((entry: any, index: number) => ({
				id: regularUsers.length + index + 1,
				name: `Manuell: ${entry.identifier.substring(0, 8)}`,
				userId: undefined,
				priorityId: entry.priorityId,
				submitted: true,
				encrypted: true,
				hasData: !!entry.prioritiesEncryptedFields,
				isManual: true,
				identifier: entry.identifier,
				adminWrappedDek: entry.adminWrappedDek,
				userEncryptedFields: null,
				prioritiesEncryptedFields: entry.prioritiesEncryptedFields
			}));

			// Beide Typen kombinieren
			users = [...regularUsers, ...manualUsers];

			if (keyUploaded) {
				await decryptAllUsers();
			}
		} catch (err) {
			error = (err as Error).message;
			console.error('Fehler beim Abrufen der Übermittlungen:', err);
		} finally {
			isLoading = false;
		}
	}

	// Alle Benutzerdaten automatisch entschlüsseln
	async function decryptAllUsers() {
		if (!keyUploaded || users.length === 0 || isDecryptingAll) return;

		isDecryptingAll = true;
		decryptionError = '';

		decryptedUsers.clear();

		try {
			for (const user of users) {
				// Den entsprechenden Service basierend auf dem Authentifizierungsmodus verwenden
				const service = authMode === 'webauthn' ? webAuthnCryptoService : cryptoService;

				// Reguläre Benutzerübermittlungen verarbeiten
				if (
					!user.isManual &&
					user.adminWrappedDek &&
					user.userEncryptedFields &&
					user.prioritiesEncryptedFields
				) {
					try {
						const result = await service.decryptUserData({
							adminWrappedDek: user.adminWrappedDek,
							userEncryptedFields: user.userEncryptedFields,
							prioritiesEncryptedFields: user.prioritiesEncryptedFields
						});

						decryptedUsers.set(user.name, {
							userName: result.userData?.name || user.name,
							userData: result.userData!,
							priorities: result.priorities!
						});
					} catch (err) {
						console.error(`Fehler beim Entschlüsseln der Daten für ${user.name}:`, err);
					}
				}
				// Manuelle Einträge verarbeiten (keine userEncryptedFields, Benutzername in priorities.name)
				else if (user.isManual && user.adminWrappedDek && user.prioritiesEncryptedFields) {
					try {
						const result = await service.decryptUserData({
							adminWrappedDek: user.adminWrappedDek,
							prioritiesEncryptedFields: user.prioritiesEncryptedFields
						});

						// Benutzernamen aus priorities.name extrahieren
						const userName = (result.priorities as any)?.name || user.identifier || user.name;

						decryptedUsers.set(user.name, {
							userName: userName,
							userData: { name: userName }, // Minimales userData-Objekt erstellen
							priorities: result.priorities!
						});
					} catch (err) {
						console.error(`Fehler beim Entschlüsseln des manuellen Eintrags ${user.name}:`, err);
					}
				}
			}

			showOverview = true;
		} catch (err) {
			console.error('Fehler während der Stapelentschlüsselung:', err);
			decryptionError = 'Einige Daten konnten nicht entschlüsselt werden';
		} finally {
			isDecryptingAll = false;
		}
	}
	// Entschlüsselten Namen für die Anzeige abrufen
	function getDisplayName(userName: string): string {
		const decrypted = decryptedUsers.get(userName);
		return decrypted?.userName || userName;
	}

	function isDecrypted(userName: string): boolean {
		return decryptedUsers.has(userName);
	}

	async function handleKeyUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files[0]) {
			keyFile = input.files[0];
			decryptionError = '';

			try {
				await cryptoService.loadPrivateKey(keyFile);
				keyUploaded = true;
				await decryptAllUsers();
			} catch (err) {
				const error = err as Error;

				if (error.message.includes('passphrase-protected')) {
					pendingKeyFile = keyFile;
					keyFile = null;
					showPassphrasePrompt = true;
				} else {
					decryptionError = error.message;
					keyFile = null;
				}
			}
		}
	}

	async function submitPassphrase() {
		if (!pendingKeyFile || !passphraseInput) return;

		try {
			await cryptoService.loadPrivateKey(pendingKeyFile, passphraseInput);
			keyFile = pendingKeyFile;
			keyUploaded = true;
			showPassphrasePrompt = false;
			passphraseInput = '';
			pendingKeyFile = null;
			await decryptAllUsers();
		} catch {
			decryptionError = 'Falsche Passphrase oder ungültiger Schlüssel';
		}
	}

	function cancelPassphrase() {
		showPassphrasePrompt = false;
		passphraseInput = '';
		pendingKeyFile = null;
	}

	async function handleKeyDrop(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
			keyFile = event.dataTransfer.files[0];
			decryptionError = '';

			try {
				await cryptoService.loadPrivateKey(keyFile);
				keyUploaded = true;
				await decryptAllUsers();
			} catch (err) {
				const error = err as Error;

				if (error.message.includes('passphrase-protected')) {
					pendingKeyFile = keyFile;
					keyFile = null;
					showPassphrasePrompt = true;
				} else {
					decryptionError = error.message;
					keyFile = null;
				}
			}
		}
	}

	/// Callback-Funktion, wenn Schlüssel entfernt wird -> alle Daten löschen
	function removeKey() {
		keyUploaded = false;
		keyFile = null;
		authMode = null;
		cryptoService.clearKey();
		webAuthnCryptoService.clearKey();
		decryptionError = '';
		decryptedUsers.clear();
		showOverview = false;
	}

	/// Callback-Funktion bei Authentifizierung mit YubiKey -> Entschlüsselung umschalten
	async function handleYubiKeyAuth() {
		isDecrypting = true;
		decryptionError = '';

		try {
			await webAuthnCryptoService.authenticateWithYubiKey();
			keyUploaded = true;
			authMode = 'webauthn';
			await decryptAllUsers();
		} catch (err) {
			const errorMsg = (err as Error).message;
			if (errorMsg.includes('NotAllowedError')) {
				decryptionError =
					'YubiKey-Authentifizierung abgebrochen. Bitte berühren Sie Ihren YubiKey bei Aufforderung.';
			} else {
				decryptionError = errorMsg;
			}
			throw err;
		} finally {
			isDecrypting = false;
		}
	}

	/// Callback-Funktion, wenn die Ansicht eines bestimmten Benutzers angefordert wird
	async function viewUserData(user: UserDisplay) {
		if (!keyUploaded) {
			decryptionError = 'Bitte authentifizieren Sie sich zuerst';
			return;
		}

		const cached = decryptedUsers.get(user.name);
		if (cached) {
			decryptedData = cached;
			showDecryptedModal = true;
			return;
		}

		if (!user.adminWrappedDek || !user.userEncryptedFields || !user.prioritiesEncryptedFields) {
			decryptionError = 'Unvollständige Daten für diesen Benutzer';
			return;
		}

		isDecrypting = true;
		decryptionError = '';

		try {
			// Den entsprechenden Service basierend auf dem Authentifizierungsmodus verwenden
			const service = authMode === 'webauthn' ? webAuthnCryptoService : cryptoService;

			const result = await service.decryptUserData({
				adminWrappedDek: user.adminWrappedDek,
				userEncryptedFields: user.userEncryptedFields,
				prioritiesEncryptedFields: user.prioritiesEncryptedFields
			});

			decryptedUsers.set(user.name, {
				userName: result.userData?.name || user.name,
				userData: result.userData!,
				priorities: result.priorities!
			});

			decryptedData = {
				userName: result.userData?.name || user.name,
				userData: result.userData!,
				priorities: result.priorities!
			};
			showDecryptedModal = true;
		} catch (err) {
			console.error('Entschlüsselungsfehler:', err);
			decryptionError = (err as Error).message;
		} finally {
			isDecrypting = false;
		}
	}

	function closeDecryptedModal() {
		showDecryptedModal = false;
		decryptedData = null;
	}

	function exportToExcel() {
		alert('Excel-Export wird noch implementiert');
	}

	function openManualEntry() {
		showManualEntry = true;
	}

	function openVacationDayModal() {
		showVacationDayModal = true;
	}

	// Fetch vacation days from API
	async function fetchVacationDays() {
		try {
			vacationDays = await apiService.getVacationDays();
		} catch (err) {
			console.error('Fehler beim Abrufen der Abwesenheitstage:', err);
		}
	}

	// Create or update a vacation day
	async function handleSaveVacationDay(date: string, type: VacationDayType, description: string) {
		await apiService.createVacationDay({ date, type, description });
		await fetchVacationDays();
		successMessage = 'Abwesenheitstag erfolgreich gespeichert!';
		showSuccessToast = true;
		setTimeout(() => {
			showSuccessToast = false;
		}, 3000);
	}

	async function handleUpdateVacationDay(date: string, type: VacationDayType, description: string) {
		await apiService.updateVacationDay(date, { type, description });
		await fetchVacationDays();
		successMessage = 'Abwesenheitstag erfolgreich aktualisiert!';
		showSuccessToast = true;
		setTimeout(() => {
			showSuccessToast = false;
		}, 3000);
	}

	async function handleDeleteVacationDay(date: string) {
		await apiService.deleteVacationDay(date);
		await fetchVacationDays();
		successMessage = 'Abwesenheitstag erfolgreich gelöscht!';
		showSuccessToast = true;
		setTimeout(() => {
			showSuccessToast = false;
		}, 3000);
	}

	// User management handlers
	function openEditUser(user: UserDisplay) {
		editingUser = user;
		showUserEditModal = true;
	}

	function closeEditUser() {
		showUserEditModal = false;
		editingUser = null;
	}

	async function handleUserEditSuccess() {
		await fetchUserSubmissions();
		successMessage = 'Benutzer erfolgreich aktualisiert!';
		showSuccessToast = true;
		setTimeout(() => {
			showSuccessToast = false;
		}, 3000);
	}

	function openDeleteUser(user: UserDisplay) {
		deletingUser = user;
		showDeleteUserConfirm = true;
	}

	function closeDeleteUser() {
		showDeleteUserConfirm = false;
		deletingUser = null;
	}

	async function confirmDeleteUser() {
		if (!deletingUser?.userId) return;

		try {
			const result = await apiService.deleteUser(deletingUser.userId);
			await fetchUserSubmissions();
			await fetchTotalUsers();
			successMessage = result.message;
			showSuccessToast = true;
			setTimeout(() => {
				showSuccessToast = false;
			}, 3000);
			closeDeleteUser();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Fehler beim Löschen des Benutzers';
			closeDeleteUser();
		}
	}

	// Priority management handlers
	function openDeletePriority(user: UserDisplay) {
		deletingPriority = user;
		showDeletePriorityConfirm = true;
	}

	function closeDeletePriority() {
		showDeletePriorityConfirm = false;
		deletingPriority = null;
	}

	async function confirmDeletePriority() {
		if (!deletingPriority?.priorityId) return;

		try {
			const result = await apiService.deletePriority(deletingPriority.priorityId);
			await fetchUserSubmissions();

			// Remove from decrypted users cache if present
			if (deletingPriority.name) {
				decryptedUsers.delete(deletingPriority.name);
			}

			successMessage = result.message;
			showSuccessToast = true;
			setTimeout(() => {
				showSuccessToast = false;
			}, 3000);
			closeDeletePriority();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Fehler beim Löschen der Priorität';
			closeDeletePriority();
		}
	}

	async function handleRefresh() {
		if (isRefreshing || isLoading) return;

		isRefreshing = true;
		error = '';
		decryptionError = '';

		try {
			await Promise.all([fetchTotalUsers(), fetchUserSubmissions()]);
		} catch (err) {
			error = 'Fehler beim Aktualisieren der Daten';
			console.error('Aktualisierungsfehler:', err);
		} finally {
			isRefreshing = false;
		}
	}

	async function handleManualSubmit(data: {
		identifier: string;
		month: string;
		weeks: WeekPriority[];
	}) {
		try {
			const result = await apiService.submitManualPriority(data.identifier, data.month, data.weeks);

			// Erfolgsbenachrichtigung anzeigen
			successMessage = result.message || 'Erfolgreich gespeichert!';
			showSuccessToast = true;

			// Automatisch nach 3 Sekunden ausblenden
			setTimeout(() => {
				showSuccessToast = false;
			}, 3000);

			// Modal schließen
			showManualEntry = false;

			// Daten aktualisieren, um neuen Eintrag anzuzeigen
			await fetchUserSubmissions();
		} catch (err) {
			decryptionError = err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten';
		}
	}
	async function handleManualSubmitAndContinue(data: {
		identifier: string;
		month: string;
		weeks: WeekPriority[];
	}) {
		try {
			const result = await apiService.submitManualPriority(data.identifier, data.month, data.weeks);

			// Erfolgsbenachrichtigung anzeigen
			successMessage = result.message || 'Erfolgreich gespeichert!';
			showSuccessToast = true;

			// Automatisch nach 3 Sekunden ausblenden
			setTimeout(() => {
				showSuccessToast = false;
			}, 3000);

			// Modal NICHT schließen - Benutzer kann weiter eingeben

			// Daten aktualisieren, um neuen Eintrag anzuzeigen
			await fetchUserSubmissions();
		} catch (err) {
			decryptionError = err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten';
		}
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<!-- Kopfzeile - Für Mobilgeräte optimiert -->
	<div class="border-b bg-white shadow-md dark:bg-gray-800">
		<div class="mx-auto max-w-7xl px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h1 class="text-2xl font-bold text-gray-800 sm:text-3xl dark:text-white">
						Admin-Dashboard
					</h1>
					<p class="mt-1 text-xs text-gray-600 sm:text-sm dark:text-gray-300">
						Benutzerübermittlungen verwalten und Daten exportieren
					</p>
				</div>
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
					<select
						bind:value={selectedMonth}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm shadow-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500 sm:w-auto dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					>
						{#each monthOptions as month (month)}
							<option value={month}>{month}</option>
						{/each}
					</select>

					<button
						type="button"
						onclick={handleRefresh}
						disabled={isRefreshing || isLoading}
						class="flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
						title="Daten aktualisieren"
					>
						<Refresh class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
						<span>
							{isRefreshing ? 'Aktualisiere...' : 'Aktualisieren'}
						</span>
					</button>
				</div>
			</div>
		</div>
	</div>

	<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
		<!-- Fehlermeldungen -->
		{#if error}
			<ErrorDisplay message={error} onClose={() => (error = '')} />
		{/if}

		{#if decryptionError}
			<ErrorDisplay
				message={decryptionError}
				title="Entschlüsselungsfehler"
				onClose={() => (decryptionError = '')}
			/>
		{/if}

		<!-- Fortschrittsindikatoren -->
		{#if isDecryptingAll}
			<LoadingIndicator
				message="Entschlüssele Benutzerdaten... ({decryptedUsers.size}/{users.length})"
			/>
		{/if}

		{#if isRefreshing}
			<LoadingIndicator
				message="Aktualisiere Daten{keyUploaded ? ' und entschlüssele...' : '...'}"
				color="blue"
			/>
		{/if}

		<!-- Ladezustand -->
		{#if isLoading}
			<div class="flex items-center justify-center py-12">
				<div class="text-center">
					<div
						class="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-purple-200 border-t-purple-600 dark:border-purple-900 dark:border-t-purple-400"
					></div>
					<p class="text-gray-600 dark:text-gray-300">Lade Daten...</p>
				</div>
			</div>
		{:else}
			<!-- Statistikkarten -->
			<StatsCards {stats} />

			<!-- Prioritäten-Übersichtstabelle -->
			{#if keyUploaded && decryptedUsers.size > 0}
				<PrioritiesOverview
					{showOverview}
					{decryptedUsers}
					{overviewData}
					{allWeeks}
					onToggle={() => (showOverview = !showOverview)}
				/>
			{/if}

			<!-- Hauptlayout - Gestapelt auf Mobilgeräten, nebeneinander auf Desktop -->
			<div class="flex flex-col gap-6 lg:grid lg:grid-cols-3 lg:gap-8">
				<!-- Hauptinhaltsbereich (Volle Breite auf Mobilgeräten, 2/3 auf Desktop) -->
				<div class="space-y-6 lg:col-span-2">
					<!-- Privater Schlüssel-Upload -->
					<AuthenticationPanel
						{keyUploaded}
						{keyFile}
						{showPassphrasePrompt}
						{passphraseInput}
						decryptedUsersCount={decryptedUsers.size}
						onKeyUpload={handleKeyUpload}
						onKeyDrop={handleKeyDrop}
						onPassphraseChange={(value) => (passphraseInput = value)}
						onSubmitPassphrase={submitPassphrase}
						onCancelPassphrase={cancelPassphrase}
						onRemoveKey={removeKey}
						onYubiKeyAuth={handleYubiKeyAuth}
					/>

					<!-- Benutzerübermittlungstabelle -->
					<UserSubmissionsTable
						{filteredUsers}
						{searchQuery}
						{keyUploaded}
						{isDecrypting}
						totalUsers={users.length}
						{isDecrypted}
						{getDisplayName}
						onSearchChange={(value) => (searchQuery = value)}
						onViewUser={viewUserData}
						onManualEntry={openManualEntry}
						onEditUser={openEditUser}
						onDeleteUser={openDeleteUser}
						onDeletePriority={openDeletePriority}
					/>
				</div>

				<!-- Seitenleisten-Aktionen (Volle Breite auf Mobilgeräten, 1/3 auf Desktop) -->
				<div class="lg:col-span-1">
					<SidebarActions
						{keyUploaded}
						{stats}
						decryptedUsersCount={decryptedUsers.size}
						onManualEntry={openManualEntry}
						onExportExcel={exportToExcel}
						onManageVacationDays={openVacationDayModal}
					/>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Modale Dialoge -->
{#if showDecryptedModal && decryptedData}
	<DecryptedDataModal
		userName={decryptedData.userName}
		userData={decryptedData.userData}
		priorities={decryptedData.priorities}
		onClose={closeDecryptedModal}
	/>
{/if}

{#if showManualEntry}
	<ManualEntryModal
		onClose={() => {
			showManualEntry = false;
		}}
		onSubmit={handleManualSubmit}
		onSubmitAndContinue={handleManualSubmitAndContinue}
	/>
{/if}

{#if showVacationDayModal}
	<VacationDayModal
		onClose={() => {
			showVacationDayModal = false;
		}}
		onSave={handleSaveVacationDay}
		onUpdate={handleUpdateVacationDay}
		onDelete={handleDeleteVacationDay}
		{vacationDays}
	/>
{/if}

<!-- User Edit Modal -->
<UserEditModal
	bind:isOpen={showUserEditModal}
	userId={editingUser?.userId || null}
	userName={editingUser?.name || ''}
	onClose={closeEditUser}
	onSuccess={handleUserEditSuccess}
/>

<!-- Delete User Confirmation -->
<ConfirmDialog
	bind:isOpen={showDeleteUserConfirm}
	title="Benutzer löschen"
	message="Möchten Sie den Benutzer '{deletingUser?.name}' wirklich löschen? Dies wird auch alle zugehörigen Prioritätsdaten unwiderruflich entfernen."
	confirmText="Benutzer löschen"
	cancelText="Abbrechen"
	variant="danger"
	onConfirm={confirmDeleteUser}
	onCancel={closeDeleteUser}
/>

<!-- Delete Priority Confirmation -->
<ConfirmDialog
	bind:isOpen={showDeletePriorityConfirm}
	title="Prioritäten löschen"
	message="Möchten Sie die Prioritätsdaten für '{deletingPriority?.name}' wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden."
	confirmText="Prioritäten löschen"
	cancelText="Abbrechen"
	variant="warning"
	onConfirm={confirmDeletePriority}
	onCancel={closeDeletePriority}
/>

<!-- Erfolgsbenachrichtigung (Toast) -->
{#if showSuccessToast}
	<div
		class="fixed right-6 bottom-6 z-50 flex items-center gap-3 rounded-lg bg-green-600 px-6 py-4 text-white shadow-2xl dark:bg-green-500"
		transition:scale={{ duration: 200, start: 0.8 }}
	>
		<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
		</svg>
		<span class="font-medium">{successMessage}</span>
	</div>
{/if}
