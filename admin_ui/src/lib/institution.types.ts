// Institution types for multi-institution support

export interface InstitutionResponse {
	id: string;
	name: string;
	short_code: string;
}

export interface InstitutionDetailResponse extends InstitutionResponse {
	registration_magic_word: string;
	admin_public_key: string;
	settings: Record<string, any> | null;
	active: boolean;
	created: string;
	updated: string;
}

export interface CreateInstitutionRequest {
	name: string;
	short_code: string;
	registration_magic_word: string;
	admin_public_key: string;
	settings?: Record<string, any>;
	active?: boolean;
}

export interface UpdateInstitutionRequest {
	name?: string;
	short_code?: string;
	registration_magic_word?: string;
	admin_public_key?: string;
	settings?: Record<string, any>;
	active?: boolean;
}

export interface UpdateMagicWordRequest {
	new_magic_word: string;
}
