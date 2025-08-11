<script lang="ts">
// @ts-nocheck
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import mermaid from 'mermaid';

	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { detectOllamaWithRetry } from '$lib/utils/ollama';
	const i18n: Writable<i18nType> = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';

	import { get, type Unsubscriber, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import {
		chatId,
		chats,
		config,
		type Model,
		models,
		tags as allTags,
		settings,
		showSidebar,
		WEBUI_NAME,
		banners,
		user,
		socket,
		showControls,
		showCallOverlay,
		currentChatPage,
		temporaryChatEnabled,
		mobile,
		showOverview,
		chatTitle,
		showArtifacts,
		toolServers,
		selectedFolder
	} from '$lib/stores';
	import { showDocumentPanel, showCourseWorkspace, toggleDocumentPanel, toggleCourseWorkspace } from '$lib/stores/documentPanel.js';
	import VirtualClassroomPanel from '$lib/components/course/VirtualClassroomPanel.svelte';
	import CourseWorkspacePanel from '$lib/components/classroom/CourseWorkspacePanel.svelte';
	import { classroomEnabled, classroomEmbedInChat } from '$lib/stores/classroom';
	import { refreshChats } from '$lib/utils/chatList';
	import {
		convertMessagesToHistory,
		copyToClipboard,
		getMessageContentParts,
		createMessagesList,
		removeDetails,
		promptTemplate,
		splitStream,
		sleep,
		getPromptVariables,
		processDetails,
		removeAllDetails
	} from '$lib/utils';

	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { createNewChat, getChatById, updateChatById, getAllTags, getTagsById } from '$lib/apis/chats';
	import { getAndUpdateUserLocation, getUserSettings } from '$lib/apis/users';
	import { chatCompleted, chatAction, stopTask, getTaskIdsByChatId, generateMoACompletion } from '$lib/apis';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { uploadFile } from '$lib/apis/files';
	import { getTools } from '$lib/apis/tools';

	// Classroom course API
	import { getCourse } from '$lib/apis/classroom';

	import Banner from '../common/Banner.svelte';
	// Kept core chat components for UI parity
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/chat/Navbar.svelte';
	// Removed ChatControls import per Course brief
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import NotificationToast from '../NotificationToast.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { fade } from 'svelte/transition';

	export let chatIdProp = '';
	// Force hiding Navbar model selector for CourseChat
	export let showModelSelector = false;

	let loading = true;

	const eventTarget = new EventTarget();
	let controlPaneComponent;

	let messageInput;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	let navbarElement;

	let showEventConfirmation = false;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventCallback = null;

	let chatIdUnsubscriber: Unsubscriber | undefined;

	let selectedModels = [''];
	let atSelectedModel: Model | undefined;
	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	// Removed uploads/tools/image/web state (disabled for CourseChat)
	let selectedToolIds = [];
	let selectedFilterIds = [];
	let imageGenerationEnabled = false;
	let webSearchEnabled = false;
	let codeInterpreterEnabled = false;

	let showCommands = false;

	let chat = null;
	let tags = [];

	let history = {
		messages: {},
		currentId: null
	};

	let taskIds = null;

	// Ensure non-admin users always see the course UI wrapper (both panels on)
	$: if ($user && $user.role !== 'admin') {
		// ensure both panels visible
		toggleDocumentPanel(true); // fixed earlier typo
		toggleCourseWorkspace(true);
	}

	// Ollama availability detection (shared)
	// Start detection using the shared utility which updates the shared store
	onMount(() => {
		try {
			detectOllamaWithRetry();
		} catch (e) {}
		// Load embed preference from localStorage (guarded by browser check)
		if (browser) {
			try {
				const pref = localStorage.getItem('classroom:embed');
				if (pref !== null) {
					classroomEmbedInChat.set(pref === 'true');
				}
			} catch {}
		}
	});

	// Chat Input
	let prompt = '';
	// upload-related arrays removed from active usage
	let params = {};

	$: if (chatIdProp) {
		navigateHandler();
	}

	const navigateHandler = async () => {
		loading = true;

		prompt = '';
		messageInput?.setText('');

		selectedToolIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;

		const storageChatInput = browser
			? sessionStorage.getItem(`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`)
			: null;

		if (chatIdProp && (await loadChat())) {
			await tick();
			loading = false;
			window.setTimeout(() => scrollToBottom(), 0);

			await tick();

			if (storageChatInput) {
				try {
					const input = JSON.parse(storageChatInput);

					if (!$temporaryChatEnabled) {
						messageInput?.setText(input.prompt);
						// uploads/features are disabled in CourseChat; ignore stored files/tool settings
						codeInterpreterEnabled = input.codeInterpreterEnabled;
					}
				} catch (e) {}
			}

			const chatInput = document.getElementById('chat-input');
			chatInput?.focus();
		} else {
			await goto('/');
		}
	};

	const onSelect = async (e) => {
		const { type, data } = e;

		if (type === 'prompt') {
			// Handle prompt selection
			messageInput?.setText(data);
		}
	};

	// Save session models for UX parity; still session-only
	$: if (selectedModels && chatIdProp !== '') {
		saveSessionSelectedModels();
	}

	const saveSessionSelectedModels = () => {
		if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
			return;
		}
		if (browser) {
			sessionStorage.selectedModels = JSON.stringify(selectedModels);
		}
	};

	let oldSelectedModelIds = [''];
	$: if (JSON.stringify(selectedModelIds) !== JSON.stringify(oldSelectedModelIds)) {
		onSelectedModelIdsChange();
	}

	const onSelectedModelIdsChange = () => {
		if (oldSelectedModelIds.filter((id) => id).length > 0) {
			resetInput();
		}
		oldSelectedModelIds = selectedModelIds;
	};

	const resetInput = () => {
		console.debug('resetInput');

		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;
	};

	const showMessage = async (message) => {
		await tick();

		const _chatId = JSON.parse(JSON.stringify($chatId));
		let _messageId = JSON.parse(JSON.stringify(message.id));

		let messageChildrenIds = [];
		if (_messageId === null) {
			messageChildrenIds = Object.keys(history.messages).filter(
				(id) => history.messages[id].parentId === null
			);
		} else {
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		while (messageChildrenIds.length !== 0) {
			_messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		history.currentId = _messageId;

		await tick();
		await tick();
		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			const messageElement = document.getElementById(`message-${message.id}`);
			if (messageElement) {
				messageElement.scrollIntoView({ behavior: 'smooth' });
			}
		}

		await tick();
		saveChatHandler(_chatId, history);
	};

	interface ChatEventData { chat_id?: string; message_id?: string; data?: any; }
	const chatEventHandler = async (event: ChatEventData, cb: (arg?: any) => void) => {
		console.log(event);

		if (event.chat_id === $chatId) {
			await tick();
			let message = history.messages[event.message_id];

			if (message) {
				const type = event?.data?.type ?? null;
				const data = event?.data?.data ?? null;

				if (type === 'status') {
					if (message?.statusHistory) {
						message.statusHistory.push(data);
					} else {
						message.statusHistory = [data];
					}
				} else if (type === 'chat:completion') {
					chatCompletionEventHandler(data, message, event.chat_id);
				} else if (type === 'chat:message:delta' || type === 'message') {
					message.content += data.content;
				} else if (type === 'chat:message' || type === 'replace') {
					message.content = data.content;
				} else if (type === 'chat:message:files' || type === 'files') {
					message.files = data.files;
				} else if (type === 'chat:message:follow_ups') {
					message.followUps = data.follow_ups;

					if (autoScroll) {
						scrollToBottom('smooth');
					}
				} else if (type === 'chat:title') {
					chatTitle.set(data);
					await refreshChats(true);
				} else if (type === 'chat:tags') {
					chat = await getChatById(localStorage.token, $chatId);
					allTags.set(await getAllTags(localStorage.token));
				} else if (type === 'source' || type === 'citation') {
					if (data?.type === 'code_execution') {
						// Code execution; update existing code execution by ID, or add new one.
						if (!message?.code_executions) {
							message.code_executions = [];
						}

						const existingCodeExecutionIndex = message.code_executions.findIndex(
							(execution) => execution.id === data.id
						);

						if (existingCodeExecutionIndex !== -1) {
							message.code_executions[existingCodeExecutionIndex] = data;
						} else {
							message.code_executions.push(data);
						}

						message.code_executions = message.code_executions;
					} else {
						// Regular source.
						if (message?.sources) {
							message.sources.push(data);
						} else {
							message.sources = [data];
						}
					}
				} else if (type === 'notification') {
					const toastType = data?.type ?? 'info';
					const toastContent = data?.content ?? '';

					if (toastType === 'success') {
						toast.success(toastContent);
					} else if (toastType === 'error') {
						toast.error(toastContent);
					} else if (toastType === 'warning') {
						toast.warning(toastContent);
					} else {
						toast.info(toastContent);
					}
				} else if (type === 'confirmation') {
					eventCallback = cb;

					eventConfirmationInput = false;
					showEventConfirmation = true;

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
				} else if (type === 'execute') {
					eventCallback = cb;

					try {
						// Use Function constructor to evaluate code in a safer way
						const asyncFunction = new Function(`return (async () => { ${data.code} })()`);
						const result = await asyncFunction(); // Await the result of the async function

						if (cb) {
							cb(result);
						}
					} catch (error) {
						console.error('Error executing code:', error);
					}
				} else if (type === 'input') {
					eventCallback = cb;

					eventConfirmationInput = true;
					showEventConfirmation = true;

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
					eventConfirmationInputPlaceholder = data.placeholder;
					eventConfirmationInputValue = data?.value ?? '';
				} else {
					console.log('Unknown message type', data);
				}

				history.messages[event.message_id] = message;
			}
		}
	};

	const onMessageHandler = async (event: {
		origin: string;
		data: { type: string; text: string };
	}) => {
		if (event.origin !== window.origin) {
			return;
		}

		// Replace with your iframe's origin
		if (event.data.type === 'input:prompt') {
			console.debug(event.data.text);

			const inputElement = document.getElementById('chat-input');

			if (inputElement) {
				messageInput?.setText(event.data.text);
				inputElement.focus();
			}
		}

		if (event.data.type === 'action:submit') {
			console.debug(event.data.text);

			if (prompt !== '') {
				await tick();
				submitPrompt(prompt);
			}
		}

		if (event.data.type === 'input:prompt:submit') {
			console.debug(event.data.text);

			if (event.data.text !== '') {
				await tick();
				submitPrompt(event.data.text);
			}
		}
	};

	let pageSubscribe = null;
	// Additional state for Course-specific model binding / fallback picker
	let courseModelBannerVisible = false;
	let fallbackModels: any[] = [];
	let sessionModelId = '';

	onMount(async () => {
		loading = true;
		console.log('mounted');
		window.addEventListener('message', onMessageHandler);
		$socket?.on('chat-events', chatEventHandler);

		pageSubscribe = page.subscribe(async (p) => {
			if (p.url.pathname === '/') {
				await tick();
				initNewChat();
			}
		});

		const storageChatInput = browser
			? sessionStorage.getItem(`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`)
			: null;

		if (!chatIdProp) {
			loading = false;
			await tick();
		}

		if (storageChatInput) {
			prompt = '';
			messageInput?.setText('');

			selectedToolIds = [];
			selectedFilterIds = [];
			webSearchEnabled = false;
			imageGenerationEnabled = false;
			codeInterpreterEnabled = false;

			try {
				const input = JSON.parse(storageChatInput);

				if (!$temporaryChatEnabled) {
					messageInput?.setText(input.prompt);
					codeInterpreterEnabled = input.codeInterpreterEnabled;
				}
			} catch (e) {}
		}

		showControls.subscribe(async (value) => {
			// Pane-based controls removed; no action needed on toggle

			if (!value) {
				showCallOverlay.set(false);
				showOverview.set(false);
				showArtifacts.set(false);
			}
		});

		// Focus the chat input if present
		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();

		chats.subscribe(() => {});

		// Course model binding logic: run in browser-only block
		if (browser) {
			const courseId = get(page).params?.courseId ?? null;
			if (courseId) {
				const res = await getCourse(localStorage.token, courseId).catch(() => null);
				const course = res?.course ?? res ?? null;
				if (course) {
					// Bind course params if present
					if (course.temperature !== undefined) params.temperature = course.temperature;
					if (course.max_tokens !== undefined) params.max_tokens = course.max_tokens;
					if (course.system_prompt !== undefined) params.system = course.system_prompt;
					if (course.kb_id !== undefined) params.kb_id = course.kb_id;

					// Try to bind fixed model from global $models
					atSelectedModel = $models.find((m) => m.id === course.model_id);
					if (atSelectedModel) {
						selectedModels = [atSelectedModel.id];
					} else {
						// Course model missing or not available: fetch aggregated /api/models for session-only picker
						try {
							const modelsRes = await fetch(`${WEBUI_BASE_URL}/api/models`, {
								headers: { Accept: 'application/json', authorization: `Bearer ${localStorage.token}` }
							});
							if (modelsRes.ok) {
								const all = await modelsRes.json();
								// Filter to non-embedding chat models and ones not hidden
								fallbackModels = (all || []).filter(
									(m) =>
										!(m?.info?.meta?.hidden ?? false) &&
										!(m?.info?.meta?.embedding ?? false) &&
										(m?.id || m?.name)
								);
								courseModelBannerVisible = fallbackModels.length > 0;
							}
						} catch (e) {
							console.warn('Could not fetch /api/models for fallback', e);
						}
					}
				}
			}
		}
	});

	onDestroy(() => {
		pageSubscribe();
		chatIdUnsubscriber?.();
		window.removeEventListener('message', onMessageHandler);
		$socket?.off('chat-events', chatEventHandler);
	});

	//////////////////////////
	// Web functions (uploads removed for CourseChat)
	//////////////////////////

	//////////////////////////
	// Web functions: init / load chat
	//////////////////////////

	const initNewChat = async () => {
		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		}

		const availableModels = $models
			.filter((m) => !(m?.info?.meta?.hidden ?? false))
			.map((m) => m.id);

		// existing URL param logic maintained (but CourseChat forces single model later)
		if ($page.url.searchParams.get('models') || $page.url.searchParams.get('model')) {
			const urlModels = (
				$page.url.searchParams.get('models') ||
				$page.url.searchParams.get('model') ||
				''
			)?.split(',');

			if (urlModels.length === 1) {
				const m = $models.find((m) => m.id === urlModels[0]);
				if (!m) {
					const modelSelectorButton = document.getElementById('model-selector-0-button');
					if (modelSelectorButton) {
						modelSelectorButton.click();
						await tick();

						const modelSelectorInput = document.getElementById('model-search-input');
						if (modelSelectorInput) {
							modelSelectorInput.focus();
							modelSelectorInput.value = urlModels[0];
							modelSelectorInput.dispatchEvent(new Event('input'));
						}
					}
				} else {
					selectedModels = urlModels;
				}
			} else {
				selectedModels = urlModels;
			}

			selectedModels = selectedModels.filter((modelId) =>
				$models.map((m) => m.id).includes(modelId)
			);
		} else {
			if (sessionStorage.selectedModels) {
				selectedModels = JSON.parse(sessionStorage.selectedModels);
				sessionStorage.removeItem('selectedModels');
			} else {
				// For non-admin users, get admin-configured default models first
				if ($user?.role !== 'admin') {
					try {
						const { getModelsConfig } = await import('$lib/apis/configs');
						const modelsConfig = await getModelsConfig(localStorage.getItem('token'));
						if (modelsConfig?.DEFAULT_MODELS) {
							const defaultModelIds = modelsConfig.DEFAULT_MODELS.split(',').filter((id) => id.trim());
							if (defaultModelIds.length > 0) {
								selectedModels = defaultModelIds;
							}
						}
					} catch (error) {
						console.warn('Could not load admin default models:', error);
					}
				}

				// Fallback to user settings or config defaults if no admin defaults or if admin user
				if (!selectedModels || selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
					if ($settings?.models) {
						selectedModels = $settings?.models;
					} else if ($config?.default_models) {
						selectedModels = $config?.default_models.split(',');
					}
				}
			}
			selectedModels = selectedModels.filter((modelId) => availableModels.includes(modelId));
		}

		if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
			if (availableModels.length > 0) {
				selectedModels = [availableModels?.at(0) ?? ''];
			} else {
				selectedModels = [''];
			}
		}

		await showControls.set(false);
		await showCallOverlay.set(false);
		await showOverview.set(false);
		await showArtifacts.set(false);

		if ($page.url.pathname.includes('/c/')) {
			window.history.replaceState(history.state, '', `/`);
		}

		autoScroll = true;

		resetInput();
		await chatId.set('');
		await chatTitle.set('');

		history = {
			messages: {},
			currentId: null
		};

		params = {};

		if ($page.url.searchParams.get('code-interpreter') === 'true') {
			codeInterpreterEnabled = true;
		}

		if ($page.url.searchParams.get('tools')) {
			selectedToolIds = $page.url.searchParams
				.get('tools')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		} else if ($page.url.searchParams.get('tool-ids')) {
			selectedToolIds = $page.url.searchParams
				.get('tool-ids')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		}

		if ($page.url.searchParams.get('call') === 'true') {
			showCallOverlay.set(true);
			showControls.set(true);
		}

		if ($page.url.searchParams.get('q')) {
			const q = $page.url.searchParams.get('q') ?? '';
			messageInput?.setText(q);

			if (q) {
				if (($page.url.searchParams.get('submit') ?? 'true') === 'true') {
					await tick();
					submitPrompt(q);
				}
			}
		}

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		const userSettings = await getUserSettings(localStorage.token);

		if (userSettings) {
			settings.set(userSettings.ui);
		} else {
			settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
		}

		const chatInput = document.getElementById('chat-input');
		setTimeout(() => chatInput?.focus(), 0);
	};

	const loadChat = async () => {
		chatId.set(chatIdProp);

		if ($temporaryChatEnabled) {
			temporaryChatEnabled.set(false);
		}

		chat = await getChatById(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			tags = await getTagsById(localStorage.token, $chatId).catch(async (error) => {
				return [];
			});

			const chatContent = chat.chat;

			if (chatContent) {
				console.log(chatContent);

				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];

				if (!($user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true))) {
					selectedModels = selectedModels.length > 0 ? [selectedModels[0]] : [''];
				}

				oldSelectedModelIds = selectedModels;

				history =
					(chatContent?.history ?? undefined) !== undefined
						? chatContent.history
						: convertMessagesToHistory(chatContent.messages);

				chatTitle.set(chatContent.title);

				const userSettings = await getUserSettings(localStorage.token);

				if (userSettings) {
					await settings.set(userSettings.ui);
				} else {
					await settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
				}

				params = chatContent?.params ?? {};

				autoScroll = true;
				await tick();

				if (history.currentId) {
					for (const message of Object.values(history.messages)) {
						if (message.role === 'assistant') {
							message.done = true;
						}
					}
				}

				const taskRes = await getTaskIdsByChatId(localStorage.token, $chatId).catch((error) => {
					return null;
				});

				if (taskRes) {
					taskIds = taskRes.task_ids;
				}

				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const scrollToBottom = async (behavior = 'auto') => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTo({
				top: messagesContainerElement.scrollHeight,
				behavior
			});
		}
	};
	const chatCompletedHandler = async (chatId, modelId, responseMessageId, messages) => {
		const res = await chatCompleted(localStorage.token, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.usage ? { usage: m.usage } : {}),
				...(m.sources ? { sources: m.sources } : {})
			})),
			filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
			model_item: $models.find((m) => m.id === modelId),
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			messages.at(-1).error = { content: error };

			return null;
		});

		if (res !== null && res.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				if (message?.id) {
					// Add null check for message and message.id
					history.messages[message.id] = {
						...history.messages[message.id],
						...(history.messages[message.id].content !== message.content
							? { originalContent: history.messages[message.id].content }
							: {}),
						...message
					};
				}
			}
		}

		await tick();

		if ($chatId == chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params
				});

				await refreshChats(true);
			}
		}

		taskIds = null;
	};

	const chatActionHandler = async (chatId, actionId, modelId, responseMessageId, event = null) => {
		const messages = createMessagesList(history, responseMessageId);

		const res = await chatAction(localStorage.token, actionId, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			...(event ? { event: event } : {}),
			model_item: $models.find((m) => m.id === modelId),
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			messages.at(-1).error = { content: error };
			return null;
		});

		if (res !== null && res.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				history.messages[message.id] = {
					...history.messages[message.id],
					...(history.messages[message.id].content !== message.content
						? { originalContent: history.messages[message.id].content }
						: {}),
					...message
				};
			}
		}

		if ($chatId == chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params
				});

				await refreshChats(true);
			}
		}
	};

	const getChatEventEmitter = async (modelId: string, chatId: string = '') => {
		return setInterval(() => {
			$socket?.emit('usage', {
				action: 'chat',
				model: modelId,
				chat_id: chatId
			});
		}, 1000);
	};

	const createMessagePair = async (userPrompt) => {
		messageInput?.setText('');
		if (!atSelectedModel) {
			toast.error($i18n.t('Model not selected'));
		} else {
			const modelId = atSelectedModel.id;
			const model = $models.filter((m) => m.id === modelId).at(0);

			const messages = createMessagesList(history, history.currentId);
			const parentMessage = messages.length !== 0 ? messages.at(-1) : null;

			const userMessageId = uuidv4();
			const responseMessageId = uuidv4();

			const userMessage = {
				id: userMessageId,
				parentId: parentMessage ? parentMessage.id : null,
				childrenIds: [responseMessageId],
				role: 'user',
				content: userPrompt ? userPrompt : `[PROMPT] ${userMessageId}`,
				timestamp: Math.floor(Date.now() / 1000)
			};

			const responseMessage = {
				id: responseMessageId,
				parentId: userMessageId,
				childrenIds: [],
				role: 'assistant',
				content: `[RESPONSE] ${responseMessageId}`,
				done: true,

				model: modelId,
				modelName: model.name ?? model.id,
				modelIdx: 0,
				timestamp: Math.floor(Date.now() / 1000)
			};

			if (parentMessage) {
				parentMessage.childrenIds.push(userMessageId);
				history.messages[parentMessage.id] = parentMessage;
			}
			history.messages[userMessageId] = userMessage;
			history.messages[responseMessageId] = responseMessage;

			history.currentId = responseMessageId;

			await tick();

			if (autoScroll) {
				scrollToBottom();
			}

			if (messages.length === 0) {
				await initChatHandler(history);
			} else {
				await saveChatHandler($chatId, history);
			}
		}
	};

	const addMessages = async ({ modelId, parentId, messages }) => {
		const model = $models.filter((m) => m.id === modelId).at(0);

		let parentMessage = history.messages[parentId];
		let currentParentId = parentMessage ? parentMessage.id : null;
		for (const message of messages) {
			let messageId = uuidv4();

			if (message.role === 'user') {
				const userMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = userMessage;
				parentMessage = userMessage;
				currentParentId = messageId;
			} else {
				const responseMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					done: true,
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: 0,
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = responseMessage;
				parentMessage = responseMessage;
				currentParentId = messageId;
			}
		}

		history.currentId = currentParentId;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (messages.length === 0) {
			await initChatHandler(history);
		} else {
			await saveChatHandler($chatId, history);
		}
	};

	const chatCompletionEventHandler = async (data, message, chatId) => {
		const { id, done, choices, content, sources, selected_model_id, error, usage } = data;

		if (error) {
			await handleOpenAIError(error, message);
		}

		if (sources && !message?.sources) {
			message.sources = sources;
		}

		if (choices) {
			if (choices[0]?.message?.content) {
				// Non-stream response
				message.content += choices[0]?.message?.content;
			} else {
				// Stream response
				let value = choices[0]?.delta?.content ?? '';
				if (message.content == '' && value == '\n') {
					console.log('Empty response');
				} else {
					message.content += value;

					if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
						navigator.vibrate(5);
					}
				}
			}
		}

		if (content) {
			// REALTIME_CHAT_SAVE is disabled
			message.content = content;

			if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
				navigator.vibrate(5);
			}
		}

		if (selected_model_id) {
			message.selectedModelId = selected_model_id;
			message.arena = true;
		}

		if (usage) {
			message.usage = usage;
		}

		history.messages[message.id] = message;

		if (done) {
			message.done = true;

			if ($settings.responseAutoCopy) {
				copyToClipboard(message.content);
			}

			// Mark completion event for other consumers
			eventTarget.dispatchEvent(
				new CustomEvent('chat:finish', {
					detail: {
						id: message.id,
						content: message.content
					}
				})
			);

			history.messages[message.id] = message;

			await tick();
			if (autoScroll) {
				scrollToBottom();
			}

			await chatCompletedHandler(
				chatId,
				message.model,
				message.id,
				createMessagesList(history, message.id)
			);
		}

		console.log(data);
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (userPrompt, { _raw = false } = {}) => {
		console.log('submitPrompt', userPrompt, $chatId);

		const messages = createMessagesList(history, history.currentId);

		if (userPrompt === '') {
			toast.error($i18n.t('Please enter a prompt'));
			return;
		}

		// CourseChat requires a selected model (course-fixed or session fallback)
		if (!atSelectedModel) {
			toast.error($i18n.t('Model not selected'));
			return;
		}

		if (messages.length != 0 && messages.at(-1).done != true) {
			// Response not done
			return;
		}
		if (messages.length != 0 && messages.at(-1).error && !messages.at(-1).content) {
			// Error in response
			toast.error($i18n.t(`Oops! There was an error in the previous response.`));
			return;
		}

		messageInput?.setText('');

		// Reset chat input textarea
		if (!($settings?.richTextInput ?? true)) {
			const chatInputElement = document.getElementById('chat-input');

			if (chatInputElement) {
				await tick();
				chatInputElement.style.height = '';
			}
		}

		// Create user message
		let userMessageId = uuidv4();
		let userMessage = {
			id: userMessageId,
			parentId: messages.length !== 0 ? messages.at(-1).id : null,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			timestamp: Math.floor(Date.now() / 1000), // Unix epoch
			models: [atSelectedModel.id]
		};

		// Add message to history and Set currentId to messageId
		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		// Append messageId to childrenIds of parent message
		if (messages.length !== 0) {
			history.messages[messages.at(-1).id].childrenIds.push(userMessageId);
		}

		// focus on chat input
		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();

		saveSessionSelectedModels();

		await sendPrompt(history, userPrompt, userMessageId, { newChat: true });
	};

	const sendPrompt = async (
		_history,
		prompt: string,
		parentId: string,
		{ modelId = null, modelIdx = null, newChat = false } = {}
	) => {
		if (autoScroll) {
			scrollToBottom();
		}

		let _chatId = JSON.parse(JSON.stringify($chatId));
		_history = JSON.parse(JSON.stringify(_history));

		const responseMessageIds: Record<PropertyKey, string> = {};

		// Force single model: prefer explicit modelId, then course model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
				? [atSelectedModel.id]
				: [];

		if (selectedModelIds.length === 0) {
			toast.error($i18n.t('Model not selected'));
			return;
		}

		// Create response message for the single model
		const modelIdToUse = selectedModelIds[0];
		const model = $models.filter((m) => m.id === modelIdToUse).at(0);

		if (model) {
			let responseMessageId = uuidv4();
			let responseMessage = {
				parentId: parentId,
				id: responseMessageId,
				childrenIds: [],
				role: 'assistant',
				content: '',
				model: model.id,
				modelName: model.name ?? model.id,
				modelIdx: 0,
				timestamp: Math.floor(Date.now() / 1000) // Unix epoch
			};

			// Add message to history and Set currentId to messageId
			history.messages[responseMessageId] = responseMessage;
			history.currentId = responseMessageId;

			// Append messageId to childrenIds of parent message
			if (parentId !== null && history.messages[parentId]) {
				history.messages[parentId].childrenIds = [
					...history.messages[parentId].childrenIds,
					responseMessageId
				];
			}

			responseMessageIds[`${modelIdToUse}-0`] = responseMessageId;
		} else {
			toast.error($i18n.t(`Model {{modelId}} not found`, { modelId: modelIdToUse }));
			return;
		}

		history = history;

		// Create new chat if newChat is true and first user message
		if (newChat && _history.messages[_history.currentId].parentId === null) {
			_chatId = await initChatHandler(_history);
		}

		await tick();

		_history = JSON.parse(JSON.stringify(history));
		// Save chat after message has been created
		await saveChatHandler(_chatId, _history);

		// Send only to single model
		const modelIdToSend = selectedModelIds[0];
		const modelToSend = $models.filter((m) => m.id === modelIdToSend).at(0);
		const responseMessageId = responseMessageIds[`${modelIdToSend}-0`];
		const chatEventEmitter = await getChatEventEmitter(modelToSend.id, _chatId);

		scrollToBottom();
		await sendPromptSocket(_history, modelToSend, responseMessageId, _chatId);

		if (chatEventEmitter) clearInterval(chatEventEmitter);

		await refreshChats(true);
	};

	const sendPromptSocket = async (_history, model, responseMessageId, _chatId) => {
		const chatMessages = createMessagesList(history, history.currentId);
		const responseMessage = _history.messages[responseMessageId];
		const userMessage = _history.messages[responseMessage.parentId];

		scrollToBottom();
		eventTarget.dispatchEvent(
			new CustomEvent('chat:start', {
				detail: {
					id: responseMessageId
				}
			})
		);
		await tick();

		const stream =
			model?.info?.params?.stream_response ??
			$settings?.params?.stream_response ??
			params?.stream_response ??
			true;

		let messages = [
			params?.system || $settings.system
				? {
						role: 'system',
						content: `${promptTemplate(
							params?.system ?? $settings?.system ?? '',
							$user?.name,
							$settings?.userLocation
								? await getAndUpdateUserLocation(localStorage.token).catch((err) => {
										console.error(err);
										return undefined;
									})
								: undefined
						)}`
					}
				: undefined,
			...createMessagesList(_history, responseMessageId).map((message) => ({
				...message,
				content: processDetails(message.content)
			}))
		].filter((message) => message);

		messages = messages
			.map((message) => ({
				role: message.role,
				content: message?.merged?.content ?? message.content
			}))
			.filter((message) => message?.role === 'user' || message?.content?.trim());

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				stream: stream,
				model: model.id,
				messages: messages,
				params: {
					...$settings?.params,
					...params,
					stop:
						(params?.stop ?? $settings?.params?.stop ?? undefined)
							? (params?.stop.split(',').map((token) => token.trim()) ?? $settings.params.stop).map(
									(str) => decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
								)
							: undefined
				},

				// Features: strictly limited for CourseChat
				features: {
					image_generation: false,
					code_interpreter:
						$config?.features?.enable_code_interpreter &&
						($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter)
							? codeInterpreterEnabled
							: false,
					web_search: false,
					memory: $settings?.memory ?? false
				},
				variables: {
					...getPromptVariables(
						$user?.name,
						$settings?.userLocation
							? await getAndUpdateUserLocation(localStorage.token).catch((err) => {
									console.error(err);
									return undefined;
								})
							: undefined
					)
				},
				model_item: $models.find((m) => m.id === model.id),

				session_id: $socket?.id,
				chat_id: $chatId,
				id: responseMessageId,

				background_tasks: {
					...(!$temporaryChatEnabled &&
					(messages.length == 1 ||
						(messages.length == 2 &&
							messages.at(0)?.role === 'system' &&
							messages.at(1)?.role === 'user')) &&
					(selectedModels[0] === model.id || atSelectedModel !== undefined)
						? {
								title_generation: $settings?.title?.auto ?? true,
								tags_generation: $settings?.autoTags ?? true
							}
						: {}),
					follow_up_generation: $settings?.autoFollowUps ?? true
				},

				...(stream && (model.info?.meta?.capabilities?.usage ?? false)
					? {
							stream_options: {
								include_usage: true
							}
						}
					: {})
			},
			`${WEBUI_BASE_URL}/api`
		).catch(async (error) => {
			toast.error(`${error}`);

			responseMessage.error = {
				content: error
			};
			responseMessage.done = true;

			history.messages[responseMessageId] = responseMessage;
			history.currentId = responseMessageId;

			return null;
		});

		if (res) {
			if (res.error) {
				await handleOpenAIError(res.error, responseMessage);
			} else {
				if (taskIds) {
					taskIds.push(res.task_id);
				} else {
					taskIds = [res.task_id];
				}
			}
		}

		await tick();
		scrollToBottom();
	};

	const handleOpenAIError = async (error, responseMessage) => {
		let errorMessage = '';
		let innerError;

		if (error) {
			innerError = error;
		}

		console.error(innerError);
		if ('detail' in innerError) {
			// FastAPI error
			toast.error(innerError.detail);
			errorMessage = innerError.detail;
		} else if ('error' in innerError) {
			// OpenAI error
			if ('message' in innerError.error) {
				toast.error(innerError.error.message);
				errorMessage = innerError.error.message;
			} else {
				toast.error(innerError.error);
				errorMessage = innerError.error;
			}
		} else if ('message' in innerError) {
			// OpenAI error
			toast.error(innerError.message);
			errorMessage = innerError.message;
		}

		responseMessage.error = {
			content: $i18n.t(`Uh-oh! There was an issue with the response.`) + '\n' + errorMessage
		};
		responseMessage.done = true;

		if (responseMessage.statusHistory) {
			responseMessage.statusHistory = responseMessage.statusHistory.filter(
				(status) => status.action !== 'knowledge_search'
			);
		}

		history.messages[responseMessage.id] = responseMessage;
	};

	const stopResponse = async () => {
		if (taskIds) {
			for (const taskId of taskIds) {
				const res = await stopTask(localStorage.token, taskId).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}

			taskIds = null;

			const responseMessage = history.messages[history.currentId];
			// Set all response messages to done
			for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
				history.messages[messageId].done = true;
			}

			history.messages[history.currentId] = responseMessage;

			if (autoScroll) {
				scrollToBottom();
			}
		}
	};

	const submitMessage = async (parentId, prompt) => {
		let userPrompt = prompt;
		let userMessageId = uuidv4();

		let userMessage = {
			id: userMessageId,
			parentId: parentId,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			models: atSelectedModel ? [atSelectedModel.id] : selectedModels,
			timestamp: Math.floor(Date.now() / 1000) // Unix epoch
		};

		if (parentId !== null) {
			history.messages[parentId].childrenIds = [
				...history.messages[parentId].childrenIds,
				userMessageId
			];
		}

		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		await sendPrompt(history, userPrompt, userMessageId);
	};

	const regenerateResponse = async (message) => {
		console.log('regenerateResponse');

		if (history.currentId) {
			let userMessage = history.messages[message.parentId];
			let userPrompt = userMessage.content;

			if (autoScroll) {
				scrollToBottom();
			}

			// Use the response's model for regeneration (single-model pipeline)
			await sendPrompt(history, userPrompt, userMessage.id, {
				modelId: message.model,
				modelIdx: message.modelIdx
			});
		}
	};

	const continueResponse = async () => {
		console.log('continueResponse');
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (history.currentId && history.messages[history.currentId].done == true) {
			const responseMessage = history.messages[history.currentId];
			responseMessage.done = false;
			await tick();

			const model = $models
				.filter((m) => m.id === (responseMessage?.selectedModelId ?? responseMessage.model))
				.at(0);

			if (model) {
				await sendPromptSocket(history, model, responseMessage.id, _chatId);
			}
		}
	};

	const mergeResponses = async (messageId, responses, _chatId) => {
		console.log('mergeResponses', messageId, responses);
		const message = history.messages[messageId];
		const mergedResponse = {
			status: true,
			content: ''
		};
		message.merged = mergedResponse;
		history.messages[messageId] = message;

		try {
			const [res, controller] = await generateMoACompletion(
				localStorage.token,
				message.model,
				history.messages[message.parentId].content,
				responses
			);

			if (res && res.ok && res.body) {
				const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
				for await (const update of textStream) {
					const { value, done, sources, error, usage } = update;
					if (error || done) {
						break;
					}

					if (mergedResponse.content == '' && value == '\n') {
						continue;
					} else {
						mergedResponse.content += value;
						history.messages[messageId] = message;
					}

					if (autoScroll) {
						scrollToBottom();
					}
				}

				await saveChatHandler(_chatId, history);
			} else {
				console.error(res);
			}
		} catch (e) {
			console.error(e);
		}
	};

	const initChatHandler = async (history) => {
		let _chatId = $chatId;

		if (!$temporaryChatEnabled) {
			chat = await createNewChat(
				localStorage.token,
				{
					id: _chatId,
					title: $i18n.t('New Chat'),
					models: selectedModels,
					system: $settings.system ?? undefined,
					params: params,
					history: history,
					messages: createMessagesList(history, history.currentId),
					tags: [],
					timestamp: Date.now()
				},
				$selectedFolder?.id
			);

			_chatId = chat.id;
			await chatId.set(_chatId);

			window.history.replaceState(history.state, '', `/c/${_chatId}`);

			await tick();

			await refreshChats(true);

			selectedFolder.set(null);
		} else {
			_chatId = 'local';
			await chatId.set('local');
		}
		await tick();

		return _chatId;
	};

	const saveChatHandler = async (_chatId, history) => {
		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history, history.currentId),
					params: params
				});
				await refreshChats(true);
			}
		}
	};
</script>

<svelte:head>
	<title>
		{$chatTitle
			? `${$chatTitle.length > 30 ? `${$chatTitle.slice(0, 30)}...` : $chatTitle} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<EventConfirmDialog
	bind:show={showEventConfirmation}
	title={eventConfirmationTitle}
	message={eventConfirmationMessage}
	input={eventConfirmationInput}
	inputPlaceholder={eventConfirmationInputPlaceholder}
	inputValue={eventConfirmationInputValue}
	on:confirm={(e) => {
		if (e.detail) {
			eventCallback(e.detail);
		} else {
			eventCallback(true);
		}
	}}
	on:cancel={() => {
		eventCallback(false);
	}}
/>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? '  md:max-w-[calc(100%-260px)]'
		: ' '} w-full max-w-full flex flex-col"
	id="chat-container"
>
	{#if !loading}
		<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
			{#if $settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url ?? null}
				<div
					class="absolute {$showSidebar
						? 'md:max-w-[calc(100%-260px)] md:translate-x-[260px]'
						: ''} top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$settings?.backgroundImageUrl ??
						$config?.license_metadata?.background_image_url})  "
				/>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				/>
			{/if}

			<!-- Layout: optional classroom side panel -->
			<div class="w-full h-full flex relative max-w-full flex-grow">
				{#if $classroomEnabled && ($user?.role === 'admin' || $user?.role === 'teacher') && $classroomEmbedInChat}
					<div class="hidden md:flex flex-col w-[40%] border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850">
						<div class="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
							<h2 class="text-sm font-semibold text-gray-900 dark:text-white">Virtual Classroom</h2>
							<button class="flex items-center gap-1.5 px-2 py-1 text-xs rounded-md bg-blue-600 hover:bg-blue-700 text-white transition" on:click={() => window.open('/classroom', '_blank')} title="Open Classroom Management">
								<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M3 5a2 2 0 0 1 2-2h6.5a2 2 0 0 1 2 2v14a1 1 0 0 0-1.447.894C12.053 19.61 11.552 19 11 19H5a2 2 0 0 0-2 2V5Zm11.5 0a2 2 0 0 1 2-2H21a2 2 0 0 1 2 2v16a2 2 0 0 0-2-2h-6.5a2 2 0 0 0-2 2V5Z" /></svg>
								Manage
							</button>
						</div>
						<div class="flex-1 overflow-auto">
							<VirtualClassroomPanel />
						</div>
					</div>
				{/if}
				<div class="flex-1 flex flex-col">
					<Navbar
						bind:this={navbarElement}
						chat={{
							id: $chatId,
							chat: {
								title: $chatTitle,
								models: selectedModels,
								system: $settings.system ?? undefined,
								params: params,
								history: history,
								timestamp: Date.now()
							}
						}}
						{history}
						title={$chatTitle}
						bind:selectedModels
						shareEnabled={!!history.currentId}
						showModelSelector={false}
						{initNewChat}
						showBanners={!showCommands}
					/>

					{#if courseModelBannerVisible}
						<div class="w-full px-4 py-2 bg-yellow-50 dark:bg-yellow-900/10 border-b border-yellow-200 dark:border-yellow-800 text-sm flex items-center justify-between gap-3">
							<div class="text-sm">Select a model for this session</div>
							<div class="flex items-center gap-2">
								<select class="border rounded px-2 py-1 bg-white dark:bg-gray-800 text-sm" bind:value={sessionModelId}>
									<option value="">-- choose a model --</option>
									{#each fallbackModels as m}
										<option value={m.id}>{m.name ?? m.id}</option>
									{/each}
								</select>
								<button class="btn btn-sm" on:click={() => {
									if (sessionModelId) {
										// Set session-only model
										atSelectedModel = fallbackModels.find(m => m.id === sessionModelId);
										selectedModels = [sessionModelId];
										courseModelBannerVisible = false;
									} else {
										toast.error($i18n.t('Please select a model'));
									}
								}}>Use</button>
							</div>
						</div>
					{/if}

					<div class="flex flex-col flex-auto z-10 w-full @container overflow-auto">
						{#if ($settings?.landingPageMode === 'chat' && !$selectedFolder) || createMessagesList(history, history.currentId).length > 0}
							<div
								class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
								id="messages-container"
								bind:this={messagesContainerElement}
								on:scroll={(e) => {
									autoScroll =
										messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
										messagesContainerElement.clientHeight + 5;
								}}
							>
								<div class=" h-full w-full flex flex-col">
									<Messages
										chatId={$chatId}
										bind:history
										bind:autoScroll
										bind:prompt
										setInputText={(text) => {
											messageInput?.setText(text);
										}}
										{selectedModels}
										{atSelectedModel}
										{sendPrompt}
										{showMessage}
										{submitMessage}
										{continueResponse}
										{regenerateResponse}
										{mergeResponses}
										{chatActionHandler}
										{addMessages}
										bottomPadding={false}
										{onSelect}
									/>
								</div>
							</div>

							<div class=" pb-2">
								<MessageInput
									bind:this={messageInput}
									{history}
									{taskIds}
									bind:prompt
									bind:autoScroll
									bind:codeInterpreterEnabled
									bind:atSelectedModel
									on:submit={async (e) => {
										if (e.detail) {
											await tick();
											submitPrompt(
												($settings?.richTextInput ?? true)
													? e.detail.replaceAll('\n\n', '\n')
													: e.detail
											);
										}
									}}
									transparentBackground={$settings?.backgroundImageUrl ??
										$config?.license_metadata?.background_image_url ?? false}
									{stopResponse}
									{createMessagePair}
									onChange={(input) => {
										if (!$temporaryChatEnabled && browser) {
											if (input.prompt !== null) {
												sessionStorage.setItem(
													`chat-input${$chatId ? `-${$chatId}` : ''}`,
													JSON.stringify(input)
												);
											} else {
												sessionStorage.removeItem(`chat-input${$chatId ? `-${$chatId}` : ''}`);
											}
										}
									}}
								/>

								<div
									class="absolute bottom-1 text-xs text-gray-500 text-center line-clamp-1 right-0 left-0"
								>
									<!-- {$i18n.t('LLMs can make mistakes. Verify important information.')} -->
								</div>
							</div>
						{:else}
							<div class="flex items-center h-full">
								<Placeholder
									{history}
									bind:messageInput
									bind:prompt
									bind:autoScroll
									bind:codeInterpreterEnabled
									bind:atSelectedModel
									bind:showCommands
									transparentBackground={$settings?.backgroundImageUrl ??
										$config?.license_metadata?.background_image_url ??
										false}
									selectedModels={selectedModels}
									{stopResponse}
									{createMessagePair}
									{onSelect}
									on:submit={async (e) => {
										if (e.detail) {
											await tick();
											submitPrompt(
												($settings?.richTextInput ?? true)
													? e.detail.replaceAll('\n\n', '\n')
													: e.detail
											);
										}
									}}
								/>
							</div>
						{/if}
					</div>

				</div> <!-- end inner chat flex -->
			</div> <!-- end layout wrapper -->
		</div> <!-- end fade container -->
	{:else}
		<div class=" flex items-center justify-center h-full w-full">
			<div class="m-auto">
				<Spinner className="size-5" />
			</div>
		</div>
	{/if}
</div>
