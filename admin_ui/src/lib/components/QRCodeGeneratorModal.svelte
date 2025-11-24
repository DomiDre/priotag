<script lang="ts">
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import Close from 'virtual:icons/mdi/close';
	import Download from 'virtual:icons/mdi/download';
	import Printer from 'virtual:icons/mdi/printer';
	import QRCode from 'qrcode';
	import { Document, Packer, Paragraph, ImageRun, TextRun, AlignmentType } from 'docx';
	import { apiService } from '$lib/api.service';
	import { env } from '$env/dynamic/public';

	interface Props {
		isOpen: boolean;
		onClose: () => void;
	}

	let { isOpen = $bindable(), onClose }: Props = $props();

	let qrDataUrl = $state('');
	let institutionName = $state('');
	let magicWord = $state('');
	let shortCode = $state('');
	let isLoading = $state(false);
	let error = $state('');

	$effect(() => {
		if (isOpen) {
			loadQRData();
		}
	});

	async function loadQRData() {
		isLoading = true;
		error = '';

		try {
			const response = await apiService.getQRRegistrationData();

			if (response.success) {
				institutionName = response.data.institution_name;
				magicWord = response.data.magic_word;
				shortCode = response.data.institution_short_code;

				// Get the app URL from environment variable
				const appUrl = env.PUBLIC_BACKEND_URL;

				// Build the full registration URL with institution and magic word
				const registrationUrl = `${appUrl}/register?institution=${shortCode}&magic=${magicWord}`;

				// Generate QR code from the registration URL
				qrDataUrl = await QRCode.toDataURL(registrationUrl, {
					width: 400,
					margin: 2,
					errorCorrectionLevel: 'H'
				});
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Fehler beim Laden der QR-Code-Daten';
			console.error('Error loading QR data:', err);
		} finally {
			isLoading = false;
		}
	}

	async function downloadQRCode() {
		if (!qrDataUrl) return;

		const link = document.createElement('a');
		link.download = `qr-registration-${shortCode}.png`;
		link.href = qrDataUrl;
		link.click();
	}

	async function generateDocx() {
		if (!qrDataUrl) return;

		try {
			// Convert base64 to blob
			const base64Data = qrDataUrl.split(',')[1];
			const binaryString = atob(base64Data);
			const bytes = new Uint8Array(binaryString.length);
			for (let i = 0; i < binaryString.length; i++) {
				bytes[i] = binaryString.charCodeAt(i);
			}

			const doc = new Document({
				sections: [
					{
						properties: {},
						children: [
							new Paragraph({
								alignment: AlignmentType.CENTER,
								spacing: { after: 400 },
								children: [
									new TextRun({
										text: 'Registrierung PrioTag',
										bold: true,
										size: 48
									})
								]
							}),
							new Paragraph({
								alignment: AlignmentType.CENTER,
								spacing: { after: 200 },
								children: [
									new TextRun({
										text: institutionName,
										bold: true,
										size: 36
									})
								]
							}),
							new Paragraph({
								alignment: AlignmentType.CENTER,
								spacing: { after: 400 },
								children: [
									new ImageRun({
										data: bytes as any,
										transformation: {
											width: 300,
											height: 300
										},
										type: 'png'
									})
								]
							}),
							new Paragraph({
								alignment: AlignmentType.CENTER,
								spacing: { after: 200 },
								children: [
									new TextRun({
										text: 'Anleitung:',
										bold: true,
										size: 28
									})
								]
							}),
							new Paragraph({
								alignment: AlignmentType.LEFT,
								spacing: { after: 200 },
								children: [
									new TextRun({
										text: '1. Scannen Sie den QR-Code mit Ihrem Smartphone',
										size: 24
									})
								]
							}),
							new Paragraph({
								alignment: AlignmentType.LEFT,
								spacing: { after: 200 },
								children: [
									new TextRun({
										text: '2. Folgen Sie dem Link zur Registrierungsseite',
										size: 24
									})
								]
							}),
							new Paragraph({
								alignment: AlignmentType.LEFT,
								spacing: { after: 200 },
								children: [
									new TextRun({
										text: '3. Erstellen Sie Ihr Konto mit Benutzername und Passwort',
										size: 24
									})
								]
							}),
							new Paragraph({
								alignment: AlignmentType.CENTER,
								spacing: { before: 400 },
								children: [
									new TextRun({
										text: 'Scannen Sie den QR-Code, um sich zu registrieren!',
										italic: true,
										size: 24
									})
								]
							})
						]
					}
				]
			});

			const blob = await Packer.toBlob(doc);

			// Create download link
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = `registrierung-${shortCode}.docx`;
			link.click();

			// Clean up
			URL.revokeObjectURL(url);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Fehler beim Generieren des Word-Dokuments';
			console.error('Error generating DOCX:', err);
		}
	}

	function printQRCode() {
		if (!qrDataUrl) return;

		const printWindow = window.open('', '_blank');
		if (!printWindow) return;

		printWindow.document.write(`
			<!DOCTYPE html>
			<html>
			<head>
				<title>QR-Code Registrierung - ${institutionName}</title>
				<style>
					body {
						font-family: Arial, sans-serif;
						display: flex;
						flex-direction: column;
						align-items: center;
						padding: 40px;
					}
					h1 {
						margin-bottom: 10px;
						font-size: 32px;
					}
					h2 {
						margin-bottom: 30px;
						font-size: 24px;
						font-weight: normal;
					}
					.qr-container {
						margin: 30px 0;
					}
					.info {
						margin-top: 30px;
						text-align: center;
					}
					.code {
						font-family: 'Courier New', monospace;
						font-size: 20px;
						font-weight: bold;
						background-color: #f0f0f0;
						padding: 10px 20px;
						border-radius: 5px;
						margin: 10px 0;
					}
					.instructions {
						margin-top: 30px;
						text-align: left;
						max-width: 600px;
					}
					.instructions li {
						margin: 10px 0;
						font-size: 16px;
					}
					@media print {
						@page {
							margin: 20mm;
						}
					}
				</style>
			</head>
			<body>
				<h1>Registrierung PrioTag</h1>
				<h2>${institutionName}</h2>
				<div class="qr-container">
					<img src="${qrDataUrl}" alt="QR Code" style="width: 300px; height: 300px;" />
				</div>
				<div class="instructions">
					<h3>So registrieren Sie sich:</h3>
					<ol>
						<li>Scannen Sie den QR-Code mit Ihrem Smartphone</li>
						<li>Folgen Sie dem Link zur Registrierungsseite</li>
						<li>Erstellen Sie Ihr Konto mit Benutzername und Passwort</li>
					</ol>
					<p style="margin-top: 30px; text-align: center; font-style: italic;">
						Der QR-Code enthält alle benötigten Informationen für die Registrierung.
					</p>
				</div>
			</body>
			</html>
		`);

		printWindow.document.close();
		setTimeout(() => {
			printWindow.print();
		}, 500);
	}

	function handleClose() {
		if (!isLoading) {
			onClose();
		}
	}
</script>

{#if isOpen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
		transition:fade={{ duration: 200 }}
		onclick={handleClose}
		onkeydown={(e) => e.key === 'Escape' && handleClose()}
		role="button"
		tabindex="-1"
	>
		<div
			class="relative w-full max-w-2xl rounded-lg bg-white shadow-2xl dark:bg-gray-800"
			transition:scale={{ duration: 200, easing: cubicOut, start: 0.95 }}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-labelledby="qr-modal-title"
			tabindex="-1"
		>
			<!-- Header -->
			<div
				class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700"
			>
				<h3 id="qr-modal-title" class="text-lg font-semibold text-gray-900 dark:text-white">
					QR-Code Registrierung
				</h3>
				<button
					type="button"
					onclick={handleClose}
					disabled={isLoading}
					class="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-900 disabled:opacity-50 dark:hover:bg-gray-700 dark:hover:text-white"
					aria-label="Schließen"
				>
					<Close class="h-5 w-5" />
				</button>
			</div>

			<!-- Content -->
			<div class="p-6">
				{#if isLoading}
					<div class="flex items-center justify-center py-12">
						<svg class="h-12 w-12 animate-spin text-purple-600" viewBox="0 0 24 24">
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
				{:else if error}
					<div
						class="rounded-lg bg-red-50 p-4 text-center text-red-800 dark:bg-red-900/20 dark:text-red-400"
					>
						{error}
					</div>
				{:else if qrDataUrl}
					<div class="space-y-6">
						<!-- Institution Info -->
						<div class="text-center">
							<h4 class="text-xl font-bold text-gray-900 dark:text-white">
								{institutionName}
							</h4>
							<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
								Dieser QR-Code ermöglicht die Registrierung neuer Benutzer
							</p>
						</div>

						<!-- QR Code Display -->
						<div class="flex justify-center">
							<div class="rounded-lg border-4 border-purple-200 p-4 dark:border-purple-800">
								<img src={qrDataUrl} alt="Registration QR Code" class="h-64 w-64" />
							</div>
						</div>

						<!-- Registration Info (for admin reference) -->
						<div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
							<p class="mb-3 text-xs text-gray-500 dark:text-gray-400">
								Referenz (nicht für Benutzer erforderlich):
							</p>
							<div class="grid grid-cols-2 gap-4">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">
										Institutionscode:
									</p>
									<p class="mt-1 font-mono text-lg font-bold text-gray-900 dark:text-white">
										{shortCode}
									</p>
								</div>
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Zauberwort:</p>
									<p class="mt-1 font-mono text-lg font-bold text-gray-900 dark:text-white">
										{magicWord}
									</p>
								</div>
							</div>
						</div>

						<!-- Instructions -->
						<div class="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
							<h5 class="mb-2 font-semibold text-blue-900 dark:text-blue-300">
								So verwenden Benutzer den QR-Code:
							</h5>
							<ol class="list-decimal space-y-1 pl-5 text-sm text-blue-800 dark:text-blue-200">
								<li>QR-Code mit Smartphone scannen</li>
								<li>Automatische Weiterleitung zur Registrierungsseite</li>
								<li>Konto mit Benutzername und Passwort erstellen</li>
							</ol>
							<p class="mt-3 text-xs text-blue-700 italic dark:text-blue-300">
								Der QR-Code enthält alle benötigten Informationen. Benutzer müssen keine Codes
								manuell eingeben.
							</p>
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div
				class="flex items-center justify-end gap-3 border-t border-gray-200 p-4 dark:border-gray-700"
			>
				<button
					type="button"
					onclick={handleClose}
					disabled={isLoading}
					class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:ring-4 focus:ring-gray-200 focus:outline-none disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:ring-gray-700"
				>
					Schließen
				</button>
				<button
					type="button"
					onclick={downloadQRCode}
					disabled={isLoading || !qrDataUrl}
					class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:ring-4 focus:ring-gray-200 focus:outline-none disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 dark:focus:ring-gray-700"
				>
					<Download class="h-4 w-4" />
					PNG
				</button>
				<button
					type="button"
					onclick={generateDocx}
					disabled={isLoading || !qrDataUrl}
					class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:ring-4 focus:ring-gray-200 focus:outline-none disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 dark:focus:ring-gray-700"
				>
					<Download class="h-4 w-4" />
					Word
				</button>
				<button
					type="button"
					onclick={printQRCode}
					disabled={isLoading || !qrDataUrl}
					class="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 focus:ring-4 focus:ring-purple-300 focus:outline-none disabled:opacity-50 dark:focus:ring-purple-800"
				>
					<Printer class="h-4 w-4" />
					Drucken
				</button>
			</div>
		</div>
	</div>
{/if}
