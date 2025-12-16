import type { Translation } from '../i18n-types';

const en = {
	// Common
	common: {
		loading: 'Loading...',
		error: 'Error',
		success: 'Success',
		cancel: 'Cancel',
		save: 'Save',
		delete: 'Delete',
		edit: 'Edit',
		confirm: 'Confirm',
		close: 'Close',
		yes: 'Yes',
		no: 'No',
		submit: 'Submit',
		back: 'Back',
		next: 'Next',
		username: 'Username',
		password: 'Password',
		email: 'Email',
		name: 'Name',
		github: 'GitHub',
		imprint: 'Imprint',
		privacy: 'Privacy',
		progress: 'Progress',
		daysCount: 'Days',
		weeksComplete: '{completed} of {total} weeks complete'
	},

	// App header/title
	app: {
		title: 'Prio Tag',
		subtitle: 'Set priority days for the month'
	},

	// Landing page
	landing: {
		hero: {
			title: 'Childcare Priority Management',
			subtitle: 'Manage childcare priorities securely with encryption and GDPR compliance.',
			loginButton: 'Log in',
			logoutButton: 'Log out',
			registerButton: 'Register',
			prioritiesButton: 'Set Priorities',
			learnMore: 'Learn more'
		},
		features: {
			title: 'Why PrioTag?',
			subtitle: 'Built with privacy and ease of use in mind',
			privacy: {
				title: 'Privacy First',
				description:
					'Server-side AES-256-GCM encryption ensures your data stays private. Only you and the administration of your childcare facility can decrypt your information.'
			},
			gdpr: {
				title: 'GDPR Compliant',
				description:
					'Full compliance with General Data Protection Regulation including minimization of the collected data, securing the data following the state of the art, as well as data export and deletion rights.'
			},
			easyToUse: {
				title: 'Easy to Use',
				description:
					'Intuitive interface for both desktop and mobile. Set weekly priorities with just a few clicks.'
			},
			multiInstitution: {
				title: 'Multi-Institution Support',
				description:
					'Supports multiple childcare facilities with separate administration and data isolation.'
			},
			secure: {
				title: 'Secure & Reliable',
				description:
					'Modern security practices with encrypted storage and secure authentication methods.'
			},
			transparent: {
				title: 'Open Source',
				description: 'Fully open source on GitHub. Review the code and contribute to development.'
			}
		},
		howItWorks: {
			title: 'How It Works',
			subtitle: 'Get started in three simple steps',
			step1: {
				title: 'Register',
				description: 'Receive a registration link or QR code from your childcare institution.'
			},
			step2: {
				title: 'Set Priorities',
				description: 'Choose your weekly childcare priorities for each weekday (Monday-Friday).'
			},
			step3: {
				title: 'Relax',
				description:
					'Your preferences are securely stored and encrypted. Administrators can generate encrypted reports.'
			}
		},
		cta: {
			title: 'Ready to get started?',
			subtitle: 'Join parents who are already managing their childcare priorities securely.',
			loginButton: 'Log in',
			registerInfo: "Don't have an account? Learn how to register →"
		},
		footer: {
			description:
				'PrioTag is an open-source childcare priority management solution with a focus on privacy.',
			links: 'Links',
			legal: 'Legal'
		}
	},

	// Authentication
	auth: {
		login: {
			title: 'Login',
			username: 'Username',
			password: 'Password',
			keepLoggedIn: 'Keep me logged in',
			keepLoggedInDesc30Days:
				'You will stay logged in for 30 days. Recommended for personal devices.',
			keepLoggedInDesc8Hours:
				'You will be logged out after 8 hours or when closing the browser. Recommended for shared computers.',
			loginButton: 'Log in',
			loggingIn: 'Logging in...',
			registerButton: 'Register',
			securityNote:
				'Stored data is encrypted server-side. We cannot read your personal information.'
		},
		register: {
			title: 'Sign Up',
			subtitle: 'Create account to enter the priority list',
			subtitleMagicWord: 'Please enter the magic word that is posted in the building',
			accessVerification: 'Access Verification',
			qrCodeDetected: 'QR code detected! You can now register.',
			privacyInfo: 'All data is end-to-end encrypted. Only you have access to your information.',
			username: 'Username',
			password: 'Password',
			passwordConfirm: 'Confirm password',
			fullName: 'Full name',
			magicWord: 'Magic word',
			keepLoggedIn: 'Keep me logged in',
			registerButton: 'Register',
			registering: 'Registering...',
			backToLogin: 'Back to login',
			backToMagicWord: '← Back to magic word entry',
			magicWordPlaceholder: 'Enter magic word',
			usernamePlaceholder: 'Enter username',
			passwordPlaceholder: 'Enter password',
			passwordConfirmPlaceholder: 'Enter password again',
			fullNamePlaceholder: 'Enter full name',
			verifyMagicWord: 'Verify magic word',
			verifying: 'Verifying...',
			verified: 'Magic word verified! You can now register.',
			magicWordInfo: 'The magic word can be found in the entrance area of the building',
			errorPasswordMismatch: 'Passwords do not match',
			errorPasswordTooShort: 'Password must be at least 1 character long',
			errorInvalidMagicWord: 'Invalid magic word',
			qrCodeRegistration: 'QR Code Registration',
			traditionalRegistration: 'Traditional Registration',
			privacyNotice: 'Privacy Notice:',
			privacyPseudonymPlaintext: '🔓 Your pseudonym (login name) is stored in plain text',
			privacyNameEncrypted: "🔒 Your child's name is stored encrypted in the database",
			childName: "Your child's name",
			encrypted: 'Encrypted',
			childNamePlaceholder: 'e.g. John Doe',
			childNameHint: 'Stored encrypted in the database',
			pseudonym: 'Pseudonym (Login name)',
			plaintext: 'Plain text',
			pseudonymPlaceholder: 'e.g. parent123',
			pseudonymHint: 'Stored in plain text. Do not use real names.',
			confirmPasswordLabel: 'Confirm password',
			confirmPasswordPlaceholder2: 'Enter password again',
			keepLoggedIn30Days: 'You will stay logged in for 30 days. Recommended for personal devices.',
			keepLoggedIn8Hours:
				'You will be logged out after 8 hours or when closing the browser. Recommended for shared computers.',
			creating: 'Creating account...',
			createAccount: 'Create account',
			alreadyHaveAccount: 'Already have an account?',
			clickToLogin: 'Click here to log in.',
			// Registration info page
			infoTitle: 'Registration Information',
			infoHeading: 'How to Register',
			infoDescription:
				'To create an account, you need a registration link from your institution administrator.',
			infoStepsTitle: 'Registration Methods:',
			infoStep1Title: 'QR Code (Recommended)',
			infoStep1Description:
				'Scan the QR code provided by your institution to register automatically.',
			infoStep2Title: 'Registration Link',
			infoStep2Description:
				'Use the registration link sent to you by your institution administrator.',
			infoStep3Title: 'Contact Administrator',
			infoStep3Description:
				"If you don't have a registration link, please contact your institution administrator.",
			infoWhyTitle: 'Why do I need this?',
			infoWhyDescription:
				'For security and privacy reasons, registration is only possible with a valid link from your institution. This ensures only authorized users can access the system.',
			infoBackToLogin: '← Back to login'
		},
		logout: 'Log out',
		reauth: {
			title: 'Re-authentication required',
			message: 'Your session has expired. Please log in again.',
			passwordPlaceholder: 'Enter password',
			loginButton: 'Log in',
			cancelButton: 'Cancel'
		}
	},

	// Priorities
	priorities: {
		title: 'Priorities',
		labels: {
			veryImportant: 'Very important',
			important: 'Important',
			normal: 'Normal',
			lessImportant: 'Less important',
			unimportant: 'Unimportant'
		},
		days: {
			monday: 'Monday',
			tuesday: 'Tuesday',
			wednesday: 'Wednesday',
			thursday: 'Thursday',
			friday: 'Friday'
		},
		selectMonth: 'Select month',
		selectYear: 'Select year',
		currentMonth: 'Current month',
		saveChanges: 'Save changes',
		saving: 'Saving...',
		saved: 'Saved',
		savedSuccess: 'Priorities saved successfully',
		errorSaving: 'Error saving',
		errorSavingRetry: 'Error saving. Please try again.',
		errorUniquePriorities: 'Each weekday must have a unique priority',
		noDataForMonth: 'No data for this month',
		clickToSetPriority: 'Click to set priority',
		holiday: 'Holiday',
		vacation: 'Vacation',
		weekend: 'Weekend',
		// Status labels
		open: 'Open',
		complete: '✓ Complete',
		// Edit modal
		week: 'Week',
		view: 'view',
		edit: 'edit',
		closeWindow: 'Close window',
		weekStartedWarning: 'This week has already started and can no longer be edited.',
		weekAlreadyStartedTooltip: 'Week already started',
		allDaysAssigned: 'All days have a priority assigned!',
		allDaysHavePriority: '✅ All days have a priority!',
		done: 'Done',
		publicHoliday: '🎉 Holiday',
		vacationDay: '🏖️ Vacation',
		absent: '📋 Absent',
		priority: 'Priority',
		priorityCannotBeSet: 'Priorities cannot be set for absence days',
		weekAlreadyStarted: 'This week has already started and can no longer be edited',
		swapPriority: 'Swap priority {priority} (currently at {day})',
		selectPriority: 'Select priority {priority}',
		swapWith: 'Swap with {day}',
		priorityNumber: 'Priority {priority}',
		willBeSwapped: 'Will be swapped',
		locked: 'Locked'
	},

	// Dashboard
	dashboard: {
		title: 'Dashboard',
		welcome: 'Welcome back!',
		welcomeBack: 'Welcome back',
		overview: 'Overview',
		allWeeksComplete: 'Awesome! All weeks for {month} are prioritized!',
		overviewForMonth: 'Here is your overview for {month}',
		selectMonth: 'Select month:',
		loading: 'Loading Dashboard...',
		statistics: 'Statistics',
		recentActivity: 'Recent activity',
		noPrioritiesSet: 'No priorities set',
		setPriorities: 'Set priorities',
		thisMonth: 'This month',
		thisWeek: 'This week',
		today: 'Today',
		upcomingVacation: 'Upcoming vacation',
		noUpcomingVacation: 'No upcoming vacation',
		progress: 'Progress',
		focusDay: 'Focus Day',
		relaxedDay: 'Relaxed Day',
		oftenHighPriority: 'Often with high priority (4-5)',
		oftenLowPriority: 'Often with low priority (1-2)',
		noData: 'No data',
		daysPrioritized: '{count} of {total} days prioritized',
		weekOverview: 'Week Overview - {month}',
		week: 'Week',
		complete: 'Complete',
		inProgress: 'In Progress',
		nextWeekToWorkOn: 'Next week to work on: Week {weekNumber}',
		editNow: 'Edit now →',
		accountManagement: 'Account Management',
		accountManagementDesc: 'Change password, View saved data, Delete account',
		manageAccount: 'Manage account →'
	},

	// Account/Settings
	account: {
		title: 'Account',
		settings: 'Settings',
		profile: 'Profile',
		security: 'Security',
		preferences: 'Preferences',
		language: 'Language',
		selectLanguage: 'Select language',
		changePassword: 'Change password',
		currentPassword: 'Current password',
		newPassword: 'New password',
		confirmNewPassword: 'Confirm new password',
		updateProfile: 'Update profile',
		deleteAccount: 'Delete account',
		deleteAccountConfirm:
			'Are you sure you want to delete your account? This action cannot be undone.',
		// Account page specific
		accountManagement: 'Account Management',
		accountInfo: 'Account Information',
		username: 'Username',
		notAvailable: 'Not available',
		accountCreated: 'Account created',
		lastLogin: 'Last login',
		accountStatus: 'Account Status',
		active: 'Active',
		// Password change
		changePasswordSection: '🔐 Change Password',
		currentPasswordPlaceholder: 'Enter current password',
		newPasswordPlaceholder: 'Enter new password',
		confirmPasswordPlaceholder: 'Repeat new password',
		showPasswords: 'Show passwords',
		changing: 'Changing...',
		passwordWeak: 'Weak',
		passwordMedium: 'Medium',
		passwordGood: 'Good',
		passwordStrong: 'Strong',
		// Password change messages
		errorAllFieldsRequired: 'Please fill in all fields',
		errorPasswordMismatch: 'The new passwords do not match',
		errorPasswordMustDiffer: 'The new password must be different from the current one',
		successPasswordChanged: 'Password changed successfully',
		errorChangingPassword: 'Error changing password',
		// Data management
		dataManagement: '📊 Data Management (GDPR)',
		gdprNotice:
			'Under the General Data Protection Regulation, you have the right to access, rectification, and deletion of your personal data.',
		viewStoredData: 'View stored data',
		exportData: 'Export data',
		errorFetchingData: 'Error fetching data: {error}',
		successDataExported: 'Data exported successfully',
		errorExportingData: 'Error exporting: {error}',
		// Delete account
		dangerZone: '⚠️ Danger Zone',
		deleteWarning:
			'Deleting your account is irreversible. All your data will be permanently deleted.',
		deleteAccountButton: 'Delete account',
		deleteConfirmTitle: '⚠️ Permanently delete account',
		deleteIrreversible: 'This action is irreversible! The following data will be deleted:',
		deleteItemAccount: 'Your user account and all login data',
		deleteItemPriorities: 'All saved priorities',
		deletionReport:
			'After deletion, you will receive a deletion report as proof according to GDPR Art. 17.',
		deleteConfirmPrompt: 'Enter DELETE to confirm:',
		deleteConfirmText: 'DELETE',
		deleting: 'Deleting account...',
		deleteAccountFinal: 'Permanently delete account',
		cancel: 'Cancel',
		errorDeleteConfirm: 'Please enter "DELETE" to confirm',
		errorDeleting: 'Error deleting: {error}',
		successDeleted: 'Account was deleted. Deletion report has been downloaded.',
		deletionCompleteMessage: 'Your account has been completely deleted according to GDPR Art. 17',
		// Data modal
		yourStoredData: 'Your stored data',
		close: 'Close',
		gdprDataInfo: 'ℹ️ This is a complete copy of all data we store about you (GDPR Art. 15)',
		exportAsJson: 'Export as JSON',
		// Session expired
		sessionExpiredTitle: 'Session expired',
		sessionExpiredMessage: 'Your session has expired. You will be redirected to login...',
		errorSessionExpired: 'Session expired. Please log in again.',
		errorLoadingAccountInfo: 'Error loading account information',
		loadingAccount: 'Loading account...'
	},

	// Vacation
	vacation: {
		title: 'Vacation',
		addVacation: 'Add vacation',
		editVacation: 'Edit vacation',
		deleteVacation: 'Delete vacation',
		startDate: 'Start date',
		endDate: 'End date',
		days: 'Days',
		totalVacationDays: 'Total vacation days',
		remainingVacationDays: 'Remaining vacation days',
		usedVacationDays: 'Used vacation days'
	},

	// Notifications
	notifications: {
		title: 'Notifications',
		noNotifications: 'No notifications',
		markAsRead: 'Mark as read',
		markAllAsRead: 'Mark all as read',
		clearAll: 'Clear all'
	},

	// Errors
	errors: {
		general: 'An error occurred',
		networkError: 'Network error',
		serverError: 'Server error',
		notFound: 'Not found',
		unauthorized: 'Unauthorized',
		forbidden: 'Forbidden',
		validationError: 'Validation error',
		sessionExpired: 'Session expired',
		loginFailed: 'Login failed',
		registrationFailed: 'Registration failed',
		invalidCredentials: 'Invalid credentials',
		userAlreadyExists: 'User already exists',
		passwordTooShort: 'Password too short',
		passwordMismatch: 'Passwords do not match',
		requiredField: 'This field is required',
		invalidEmail: 'Invalid email address',
		invalidDate: 'Invalid date',
		tryAgain: 'Please try again'
	},

	// Success messages
	success: {
		saved: 'Successfully saved',
		updated: 'Successfully updated',
		deleted: 'Successfully deleted',
		created: 'Successfully created',
		loginSuccess: 'Successfully logged in',
		logoutSuccess: 'Successfully logged out',
		registrationSuccess: 'Successfully registered',
		passwordChanged: 'Password successfully changed',
		profileUpdated: 'Profile successfully updated'
	},

	// Admin (minimal, as admin stays German)
	admin: {
		title: 'Admin',
		dashboard: 'Admin Dashboard'
	}
} satisfies Translation;

export default en;
