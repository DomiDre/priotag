import type { BaseTranslation } from '../i18n-types';

const de = {
	// Common
	common: {
		loading: 'Lade...',
		error: 'Fehler',
		success: 'Erfolg',
		cancel: 'Abbrechen',
		save: 'Speichern',
		delete: 'Löschen',
		edit: 'Bearbeiten',
		confirm: 'Bestätigen',
		close: 'Schließen',
		yes: 'Ja',
		no: 'Nein',
		submit: 'Absenden',
		back: 'Zurück',
		next: 'Weiter',
		username: 'Username',
		password: 'Passwort',
		email: 'E-Mail',
		name: 'Name',
		github: 'GitHub',
		imprint: 'Impressum',
		privacy: 'Datenschutz',
		progress: 'Fortschritt',
		daysCount: 'Tage',
		weeksComplete: '{completed:number} von {total:number} Wochen vollständig'
	},

	// App header/title
	app: {
		title: 'Prio Tag',
		subtitle: 'Prio Tage für den Monat festlegen'
	},

	// Authentication
	auth: {
		login: {
			title: 'Anmelden',
			username: 'Username',
			password: 'Passwort',
			keepLoggedIn: 'Angemeldet bleiben',
			keepLoggedInDesc30Days: 'Sie bleiben 30 Tage angemeldet. Empfohlen für persönliche Geräte.',
			keepLoggedInDesc8Hours:
				'Sie werden nach 8 Stunden oder beim Schließen des Browsers abgemeldet. Empfohlen für gemeinsam genutzte Computer.',
			loginButton: 'Anmelden',
			loggingIn: 'Wird angemeldet...',
			registerButton: 'Registrieren',
			securityNote:
				'Gespeicherte Daten werden Serverseitig verschlüsselt. Wir können Ihre persönlichen Informationen nicht lesen.'
		},
		register: {
			title: 'Anmelden',
			subtitle: 'Account zur Eingabe der Prioliste erstellen',
			subtitleMagicWord: 'Bitte geben Sie das Zauberwort ein, das im Gebäude hinterlegt ist',
			accessVerification: 'Zugangsverifizierung',
			qrCodeDetected: 'QR-Code erkannt! Sie können sich jetzt registrieren.',
			privacyInfo:
				'Alle Daten werden End-to-End verschlüsselt. Nur Sie haben Zugang zu Ihren Informationen.',
			username: 'Username',
			password: 'Passwort',
			passwordConfirm: 'Passwort bestätigen',
			fullName: 'Vollständiger Name',
			magicWord: 'Zauberwort',
			keepLoggedIn: 'Angemeldet bleiben',
			registerButton: 'Registrieren',
			registering: 'Wird registriert...',
			backToLogin: 'Zurück zum Login',
			backToMagicWord: '← Zurück zur Zauberwort-Eingabe',
			magicWordPlaceholder: 'Zauberwort eingeben',
			usernamePlaceholder: 'Username eingeben',
			passwordPlaceholder: 'Passwort eingeben',
			passwordConfirmPlaceholder: 'Nochmal Passwort eingeben',
			fullNamePlaceholder: 'Vollständiger Name eingeben',
			verifyMagicWord: 'Zauberwort überprüfen',
			verifying: 'Überprüfe...',
			verified: 'Zauberwort verifiziert! Sie können sich jetzt registrieren.',
			magicWordInfo: 'Das Zauberwort finden Sie im Eingangsbereich des Gebäudes',
			errorPasswordMismatch: 'Passwörter stimmen nicht überein',
			errorPasswordTooShort: 'Password must be at least 1 character long',
			errorInvalidMagicWord: 'Ungültiges Zauberwort',
			qrCodeRegistration: 'QR-Code Registrierung',
			traditionalRegistration: 'Normale Registrierung',
			privacyNotice: 'Datenschutzhinweis:',
			privacyPseudonymPlaintext: '🔓 Ihr Pseudonym (Loginname) wird im Klartext gespeichert',
			privacyNameEncrypted:
				'🔒 Der Name Ihres Kindes wird verschlüsselt in der Datenbank gespeichert',
			childName: 'Name Ihres Kindes',
			encrypted: 'Verschlüsselt',
			childNamePlaceholder: 'z.B. Max Mustermann',
			childNameHint: 'Wird verschlüsselt in der Datenbank gespeichert',
			pseudonym: 'Pseudonym (Loginname)',
			plaintext: 'Klartext',
			pseudonymPlaceholder: 'z.B. elternteil123',
			pseudonymHint: 'Wird im Klartext gespeichert. Verwenden Sie keine echten Namen.',
			confirmPasswordLabel: 'Passwort bestätigen',
			confirmPasswordPlaceholder2: 'Nochmal Passwort eingeben',
			keepLoggedIn30Days: 'Sie bleiben 30 Tage angemeldet. Empfohlen für persönliche Geräte.',
			keepLoggedIn8Hours:
				'Sie werden nach 8 Stunden oder beim Schließen des Browsers abgemeldet. Empfohlen für gemeinsam genutzte Computer.',
			creating: 'Erstelle Account...',
			createAccount: 'Account erstellen',
			alreadyHaveAccount: 'Haben Sie bereits einen Account?',
			clickToLogin: 'Hier klicken zum einloggen.',
			// Registration info page
			infoTitle: 'Registrierungsinformationen',
			infoHeading: 'Wie registrieren',
			infoDescription:
				'Um einen Account zu erstellen, benötigen Sie einen Registrierungslink von Ihrem Institutionsadministrator.',
			infoStepsTitle: 'Registrierungsmethoden:',
			infoStep1Title: 'QR-Code (Empfohlen)',
			infoStep1Description:
				'Scannen Sie den von Ihrer Institution bereitgestellten QR-Code, um sich automatisch zu registrieren.',
			infoStep2Title: 'Registrierungslink',
			infoStep2Description:
				'Verwenden Sie den Registrierungslink, den Ihnen Ihr Institutionsadministrator gesendet hat.',
			infoStep3Title: 'Administrator kontaktieren',
			infoStep3Description:
				'Wenn Sie keinen Registrierungslink haben, kontaktieren Sie bitte Ihren Institutionsadministrator.',
			infoWhyTitle: 'Warum benötige ich das?',
			infoWhyDescription:
				'Aus Sicherheits- und Datenschutzgründen ist die Registrierung nur mit einem gültigen Link von Ihrer Institution möglich. Dies stellt sicher, dass nur autorisierte Benutzer Zugang zum System haben.',
			infoBackToLogin: '← Zurück zum Login'
		},
		logout: 'Abmelden',
		reauth: {
			title: 'Erneute Anmeldung erforderlich',
			message: 'Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.',
			passwordPlaceholder: 'Passwort eingeben',
			loginButton: 'Anmelden',
			cancelButton: 'Abbrechen'
		}
	},

	// Priorities
	priorities: {
		title: 'Prioritäten',
		labels: {
			veryImportant: 'Sehr wichtig',
			important: 'Wichtig',
			normal: 'Normal',
			lessImportant: 'Weniger wichtig',
			unimportant: 'Unwichtig'
		},
		days: {
			monday: 'Montag',
			tuesday: 'Dienstag',
			wednesday: 'Mittwoch',
			thursday: 'Donnerstag',
			friday: 'Freitag'
		},
		selectMonth: 'Monat auswählen',
		selectYear: 'Jahr auswählen',
		currentMonth: 'Aktueller Monat',
		saveChanges: 'Änderungen speichern',
		saving: 'Wird gespeichert...',
		saved: 'Gespeichert',
		savedSuccess: 'Prioritäten erfolgreich gespeichert',
		errorSaving: 'Fehler beim Speichern',
		errorSavingRetry: 'Fehler beim Speichern. Bitte versuchen Sie es erneut.',
		errorUniquePriorities: 'Jeder Wochentag muss eine eindeutige Priorität haben',
		noDataForMonth: 'Keine Daten für diesen Monat',
		clickToSetPriority: 'Klicken Sie, um die Priorität zu setzen',
		holiday: 'Feiertag',
		vacation: 'Urlaub',
		weekend: 'Wochenende',
		// Status labels
		open: 'Offen',
		complete: '✓ Fertig',
		// Edit modal
		week: 'Woche',
		view: 'ansehen',
		edit: 'bearbeiten',
		closeWindow: 'Fenster schließen',
		weekStartedWarning: 'Diese Woche hat bereits begonnen und kann nicht mehr bearbeitet werden.',
		weekAlreadyStartedTooltip: 'Woche bereits gestartet',
		allDaysAssigned: 'Alle Tage haben eine Priorität zugewiesen!',
		allDaysHavePriority: '✅ Alle Tage haben eine Priorität!',
		done: 'Fertig',
		publicHoliday: '🎉 Feiertag',
		vacationDay: '🏖️ Urlaub',
		absent: '📋 Abwesend',
		priority: 'Priorität',
		priorityCannotBeSet: 'Prioritäten können nicht für Abwesenheitstage gesetzt werden',
		weekAlreadyStarted: 'Diese Woche hat bereits begonnen und kann nicht mehr bearbeitet werden',
		swapPriority: 'Priorität {priority:number} tauschen (aktuell bei {day:string})',
		selectPriority: 'Priorität {priority:number} wählen',
		swapWith: 'Tauschen mit {day:string}',
		priorityNumber: 'Priorität {priority:number}',
		willBeSwapped: 'Wird getauscht',
		locked: 'Gesperrt'
	},

	// Dashboard
	dashboard: {
		title: 'Dashboard',
		welcome: 'Willkommen zurück!',
		welcomeBack: 'Willkommen zurück',
		overview: 'Übersicht',
		allWeeksComplete: 'Super! Alle Wochen für {month:string} sind priorisiert!',
		overviewForMonth: 'Hier ist Ihre Übersicht für {month:string}',
		selectMonth: 'Monat auswählen:',
		loading: 'Lade Dashboard...',
		statistics: 'Statistiken',
		recentActivity: 'Letzte Aktivität',
		noPrioritiesSet: 'Keine Prioritäten gesetzt',
		setPriorities: 'Prioritäten setzen',
		thisMonth: 'Diesen Monat',
		thisWeek: 'Diese Woche',
		today: 'Heute',
		upcomingVacation: 'Kommender Urlaub',
		noUpcomingVacation: 'Kein kommender Urlaub',
		progress: 'Fortschritt',
		focusDay: 'Fokus-Tag',
		relaxedDay: 'Entspannter Tag',
		oftenHighPriority: 'Oft mit hoher Priorität (4-5)',
		oftenLowPriority: 'Oft mit niedriger Priorität (1-2)',
		noData: 'Keine Daten',
		daysPrioritized: '{count:number} von {total:number} Tagen priorisiert',
		weekOverview: 'Wochenübersicht - {month:string}',
		week: 'Woche',
		complete: 'Vollständig',
		inProgress: 'In Bearbeitung',
		nextWeekToWorkOn: 'Nächste zu bearbeitende Woche: Woche {weekNumber:number}',
		editNow: 'Jetzt bearbeiten →',
		accountManagement: 'Account-Verwaltung',
		accountManagementDesc: 'Passwort ändern, Gespeicherte Daten einsehen, Account löschen',
		manageAccount: 'Account verwalten →'
	},

	// Account/Settings
	account: {
		title: 'Konto',
		settings: 'Einstellungen',
		profile: 'Profil',
		security: 'Sicherheit',
		preferences: 'Einstellungen',
		language: 'Sprache',
		selectLanguage: 'Sprache auswählen',
		changePassword: 'Passwort ändern',
		currentPassword: 'Aktuelles Passwort',
		newPassword: 'Neues Passwort',
		confirmNewPassword: 'Neues Passwort bestätigen',
		updateProfile: 'Profil aktualisieren',
		deleteAccount: 'Konto löschen',
		deleteAccountConfirm:
			'Möchten Sie Ihr Konto wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.',
		// Account page specific
		accountManagement: 'Account-Verwaltung',
		accountInfo: 'Account-Informationen',
		username: 'Username',
		notAvailable: 'Nicht verfügbar',
		accountCreated: 'Account erstellt',
		lastLogin: 'Letzte Anmeldung',
		accountStatus: 'Account-Status',
		active: 'Aktiv',
		// Password change
		changePasswordSection: '🔐 Passwort ändern',
		currentPasswordPlaceholder: 'Aktuelles Passwort eingeben',
		newPasswordPlaceholder: 'Neues Passwort eingeben',
		confirmPasswordPlaceholder: 'Neues Passwort wiederholen',
		showPasswords: 'Passwörter anzeigen',
		changing: 'Wird geändert...',
		passwordWeak: 'Schwach',
		passwordMedium: 'Mittel',
		passwordGood: 'Gut',
		passwordStrong: 'Stark',
		// Password change messages
		errorAllFieldsRequired: 'Bitte füllen Sie alle Felder aus',
		errorPasswordMismatch: 'Die neuen Passwörter stimmen nicht überein',
		errorPasswordMustDiffer: 'Das neue Passwort muss sich vom aktuellen unterscheiden',
		successPasswordChanged: 'Passwort erfolgreich geändert',
		errorChangingPassword: 'Fehler beim Ändern des Passworts',
		// Data management
		dataManagement: '📊 Datenverwaltung (DSGVO)',
		gdprNotice:
			'Gemäß der Datenschutz-Grundverordnung haben Sie das Recht auf Auskunft, Berichtigung und Löschung Ihrer personenbezogenen Daten.',
		viewStoredData: 'Gespeicherte Daten einsehen',
		exportData: 'Daten exportieren',
		errorFetchingData: 'Fehler beim Abrufen der Daten: {error:string}',
		successDataExported: 'Daten erfolgreich exportiert',
		errorExportingData: 'Fehler beim Exportieren: {error:string}',
		// Delete account
		dangerZone: '⚠️ Gefahrenzone',
		deleteWarning:
			'Das Löschen Ihres Accounts ist unwiderruflich. Alle Ihre Daten werden permanent gelöscht.',
		deleteAccountButton: 'Account löschen',
		deleteConfirmTitle: '⚠️ Account dauerhaft löschen',
		deleteIrreversible: 'Diese Aktion ist unwiderruflich! Folgende Daten werden gelöscht:',
		deleteItemAccount: 'Ihr Benutzerkonto und alle Anmeldedaten',
		deleteItemPriorities: 'Alle gespeicherten Prioritäten',
		deletionReport:
			'Nach der Löschung erhalten Sie einen Löschbericht als Nachweis gemäß DSGVO Art. 17.',
		deleteConfirmPrompt: 'Geben Sie LÖSCHEN zur Bestätigung ein:',
		deleteConfirmText: 'LÖSCHEN',
		deleting: 'Lösche Account...',
		deleteAccountFinal: 'Account endgültig löschen',
		cancel: 'Abbrechen',
		errorDeleteConfirm: 'Bitte geben Sie "LÖSCHEN" zur Bestätigung ein',
		errorDeleting: 'Fehler beim Löschen: {error:string}',
		successDeleted: 'Account wurde gelöscht. Löschbericht wurde heruntergeladen.',
		deletionCompleteMessage: 'Ihr Account wurde vollständig gelöscht gemäß DSGVO Art. 17',
		// Data modal
		yourStoredData: 'Ihre gespeicherten Daten',
		close: 'Schließen',
		gdprDataInfo:
			'ℹ️ Dies ist eine vollständige Kopie aller Daten, die wir über Sie speichern (DSGVO Art. 15)',
		exportAsJson: 'Als JSON exportieren',
		// Session expired
		sessionExpiredTitle: 'Sitzung abgelaufen',
		sessionExpiredMessage:
			'Ihre Sitzung ist abgelaufen. Sie werden zur Anmeldung weitergeleitet...',
		errorSessionExpired: 'Sitzung abgelaufen. Bitte melden Sie sich erneut an.',
		errorLoadingAccountInfo: 'Fehler beim Laden der Kontoinformationen',
		loadingAccount: 'Lade Account...'
	},

	// Vacation
	vacation: {
		title: 'Urlaub',
		addVacation: 'Urlaub hinzufügen',
		editVacation: 'Urlaub bearbeiten',
		deleteVacation: 'Urlaub löschen',
		startDate: 'Startdatum',
		endDate: 'Enddatum',
		days: 'Tage',
		totalVacationDays: 'Gesamte Urlaubstage',
		remainingVacationDays: 'Verbleibende Urlaubstage',
		usedVacationDays: 'Genutzte Urlaubstage'
	},

	// Notifications
	notifications: {
		title: 'Benachrichtigungen',
		noNotifications: 'Keine Benachrichtigungen',
		markAsRead: 'Als gelesen markieren',
		markAllAsRead: 'Alle als gelesen markieren',
		clearAll: 'Alle löschen'
	},

	// Errors
	errors: {
		general: 'Ein Fehler ist aufgetreten',
		networkError: 'Netzwerkfehler',
		serverError: 'Serverfehler',
		notFound: 'Nicht gefunden',
		unauthorized: 'Nicht autorisiert',
		forbidden: 'Verboten',
		validationError: 'Validierungsfehler',
		sessionExpired: 'Sitzung abgelaufen',
		loginFailed: 'Anmeldung fehlgeschlagen',
		registrationFailed: 'Registrierung fehlgeschlagen',
		invalidCredentials: 'Ungültige Anmeldedaten',
		userAlreadyExists: 'Benutzer existiert bereits',
		passwordTooShort: 'Passwort zu kurz',
		passwordMismatch: 'Passwörter stimmen nicht überein',
		requiredField: 'Dieses Feld ist erforderlich',
		invalidEmail: 'Ungültige E-Mail-Adresse',
		invalidDate: 'Ungültiges Datum',
		tryAgain: 'Bitte versuchen Sie es erneut'
	},

	// Success messages
	success: {
		saved: 'Erfolgreich gespeichert',
		updated: 'Erfolgreich aktualisiert',
		deleted: 'Erfolgreich gelöscht',
		created: 'Erfolgreich erstellt',
		loginSuccess: 'Erfolgreich angemeldet',
		logoutSuccess: 'Erfolgreich abgemeldet',
		registrationSuccess: 'Erfolgreich registriert',
		passwordChanged: 'Passwort erfolgreich geändert',
		profileUpdated: 'Profil erfolgreich aktualisiert'
	},

	// Admin (minimal, as admin stays German)
	admin: {
		title: 'Admin',
		dashboard: 'Admin Dashboard'
	}
} satisfies BaseTranslation;

export default de;
