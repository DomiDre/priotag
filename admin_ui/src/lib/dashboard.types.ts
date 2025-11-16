// Types for admin user submission data
export interface UserPriorityRecord {
	adminWrappedDek: string;
	userName: string;
	userId: string; // PocketBase user ID
	month: string;
	userEncryptedFields: string;
	prioritiesEncryptedFields: string;
	priorityId: string; // PocketBase priority record ID for deletion
}

// Extended type for UI display with computed properties
export interface UserSubmissionDisplay extends UserPriorityRecord {
	submitted: boolean;
	encrypted: boolean;
	// These will be populated after decryption
	decryptedName?: string;
	decryptedPriorities?: DecryptedPriorities;
}

export interface UserDisplay {
	id: number;
	name: string;
	userId?: string; // PocketBase user ID (only for regular users, not manual entries)
	priorityId?: string; // PocketBase priority record ID
	submitted: boolean;
	encrypted: boolean;
	hasData: boolean;
	isManual: boolean;
	identifier?: string;
	adminWrappedDek?: string;
	userEncryptedFields?: string;
	prioritiesEncryptedFields?: string;
}

export interface Stats {
	totalUsers: number;
	submitted: number;
	pending: number;
	submissionRate: number;
}

export interface DecryptedUserData {
	name: string;
}

export interface WeekPriority {
	weekNumber: number;
	monday: number;
	tuesday: number;
	wednesday: number;
	thursday: number;
	friday: number;
}

export interface DecryptedPriorities {
	weeks: WeekPriority[];
}

export interface DecryptedData {
	userName: string;
	userData: DecryptedUserData;
	priorities: DecryptedPriorities;
}
