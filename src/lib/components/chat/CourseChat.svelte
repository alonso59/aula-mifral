<script lang="ts">
// @ts-nocheck
  import { v4 as uuidv4 } from 'uuid';
  import { toast } from 'svelte-sonner';

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
  // upload/files and tools disabled for CourseChat; imports removed

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
  // Accept `courseId` when CourseChat is used inside classroom routes and map it to chatIdProp
  // so existing initialization (navigateHandler) works without changing callers.
  export let courseId = '';
  // Optional preset provided by classroom pages (contains model(s) selected when course was created)
  export let preset = null;
  // When the parent embeds CourseChat it may pass `embedded={true}`; accept that prop.
  export let embedded = false;
  // Force hiding Navbar model selector for CourseChat
  export let showModelSelector = false;
  // keep prop for backwards compatibility; when true, parent requests hiding any embedded panels
  export let hideEmbeddedPanels = false;

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

  // Fix: Declare sessionModelId for model selection dropdown
  let sessionModelId = "";

  // Local chat files and UI flags used by CourseChat
  let chatFiles: any[] = [];
  let courseModelBannerVisible = false;
  let fallbackModels: Model[] = [];

  // Minimal resetInput implementation (mirrors Chat.resetInput behavior)
  function resetInput() {
    try {
      prompt = '';
      if (messageInput && typeof messageInput.setText === 'function') messageInput.setText('');
    } catch {}
    chatFiles = [];
    params = {};
  }

	let taskIds = null;
	let showLeftPanel = true; // left panel is the main panel for Classroom; can be hidden (unmounted) by user

	function hideLeftPanel() {
	  // persist user preference and update embed flag so other parts of the app know the panel was removed
	  showLeftPanel = true;
	  try { localStorage.setItem('classroom:leftHidden', 'true'); } catch {}
	  try { classroomEmbedInChat.set(true); } catch {}
	}

  // Ollama availability detection (lazy)
  // Do NOT run detection automatically on mount — it's network-dependent and may fail in docker
  // environments. Instead, detect Ollama only when a selected model requires it.
  onMount(() => {
    if (browser) {
      try {
        const pref = localStorage.getItem('classroom:embed');
        if (pref !== null) {
          classroomEmbedInChat.set(pref === 'true');
        }
        // Persisted preference for hiding the left panel in course chat
        const leftHidden = localStorage.getItem('classroom:leftHidden');
        if (leftHidden === 'true') {
          showLeftPanel = false;
        }
      } catch {}
    }
  });

  // When selectedModels changes, check whether any chosen model requires Ollama.
  // If so, trigger detection in the background (non-blocking).
  $: if (browser && selectedModels && selectedModels.length > 0) {
    try {
      const needsOllama = selectedModels.some((id) => {
        const m = $models.find((mm) => mm.id === id);
        return m?.info?.meta?.provider === 'ollama' || m?.info?.meta?.backend === 'ollama';
      });
      if (needsOllama) {
        // Fire-and-forget; detect implementation updates the ollamaAvailable store.
        detectOllamaWithRetry().catch(() => {});
      }
    } catch (e) {
      // Defensive: don't let UI crash if stores or models are not ready yet.
      console.debug('CourseChat: ollama detection skipped', e);
    }
  }
 

  // Chat Input
  let prompt = '';
  let params = {};

  // Support either `chatIdProp` (standalone chat) or `courseId` (classroom pages).
  // If `courseId` is provided map it to chatIdProp so navigateHandler runs.
  // Ensure navigateHandler is defined here so reactive statements can call it without causing a ReferenceError.
  async function navigateHandler() {
    try {
      loading = true;
      if (!chatIdProp || chatIdProp === '') {
        await initNewChat();
      } else {
        await loadChat();
      }
    } catch (e) {
      console.error('CourseChat.navigateHandler error', e);
    } finally {
      loading = false;
    }
  }

  // If a course preset is provided, prefer to set selectedModels from it before initializing the chat.
  $: if (browser && preset) {
    try {
      const presetModelIds =
        preset?.models ??
        (preset?.model ? (Array.isArray(preset.model) ? preset.model : [preset.model]) : null) ??
        (preset?.model_id ? (Array.isArray(preset.model_id) ? preset.model_id : [preset.model_id]) : null);
      if (
        presetModelIds &&
        Array.isArray(presetModelIds) &&
        presetModelIds.length > 0 &&
        (!selectedModels || selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === ''))
      ) {
        selectedModels = presetModelIds;
      }
    } catch (e) {
      console.debug('CourseChat: failed to apply preset models', e);
    }
  }

  $: if (browser && (chatIdProp || courseId)) {
    if (!chatIdProp && courseId) {
      chatIdProp = courseId;
    }
    navigateHandler();
  }

async function createOrLoadCourseChat(courseIdParam: string | undefined) {
	// Create a per-user chat tied to the course. We prefer creating a new chat for the user
	// with the course's preset models so the session is pre-configured.
	try {
		const modelsFromPreset =
			(preset?.models && Array.isArray(preset.models) && preset.models.length > 0 && preset.models) ||
			(preset?.model ? (Array.isArray(preset.model) ? preset.model : [preset.model]) : null) ||
			(preset?.model_id ? (Array.isArray(preset.model_id) ? preset.model_id : [preset.model_id]) : null);

		let modelsToUse = selectedModels && selectedModels.length && selectedModels[0] !== '' ? selectedModels : [];

		if ((!modelsToUse || modelsToUse.length === 0 || (modelsToUse.length === 1 && modelsToUse[0] === '')) && modelsFromPreset) {
			modelsToUse = modelsFromPreset;
		}

		// final fallback to config/defaults
		if (!modelsToUse || modelsToUse.length === 0) {
			modelsToUse = ($settings?.models ?? ($config?.default_models ? $config.default_models.split(',') : [])) || [];
		}

		const payload: any = {
			title: preset?.title ? `Course: ${preset.title}` : `Course Chat ${courseIdParam ?? ''}`,
			models: modelsToUse,
			metadata: { courseId: courseIdParam ?? null }
		};

		try {
			const res = await createNewChat(localStorage.token, payload);
			// createNewChat may return different shapes; try to extract id
			const newId = res?.id ?? res?.chat?.id ?? null;
			if (newId) {
				chatIdProp = newId;
				// let navigateHandler/loadChat pick it up
				await loadChat();
				return newId;
			}
		} catch (e: any) {
			// Friendly error handling: show toast and avoid unhandled rejections.
			console.error('createOrLoadCourseChat error', e);
			try {
				const msg = (e && (e.detail || e.message)) ? (e.detail || e.message) : 'Failed to create course chat';
				if (toast && typeof toast === 'function') toast({ message: `Course chat: ${msg}`, type: 'error', timeout: 4000 });
			} catch {}
			return null;
		}
	} catch (e) {
		console.error('createOrLoadCourseChat error', e);
	}

	// Fallback: initialize a fresh chat instance in-memory
	await initNewChat();
	return null;
}

const initNewChat = async () => {
		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		}

		const availableModels = $models
			.filter((m) => !(m?.info?.meta?.hidden ?? false))
			.map((m) => m.id);

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
						console.log($config?.default_models.split(',') ?? '');
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

		chatFiles = [];
		params = {};

		if ($page.url.searchParams.get('youtube')) {
			uploadYoutubeTranscription(
				`https://www.youtube.com/watch?v=${$page.url.searchParams.get('youtube')}`
			);
		}

		if ($page.url.searchParams.get('load-url')) {
			await uploadWeb($page.url.searchParams.get('load-url'));
		}

		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}

		if ($page.url.searchParams.get('image-generation') === 'true') {
			imageGenerationEnabled = true;
		}

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

		try {
			chat = await getChatById(localStorage.token, $chatId);
		} catch (error: any) {
			// Don't force a redirect to `/` for course-embedded flows.
			// If this component was mounted with a courseId, create a per-user chat for that course instead.
			try {
				if (courseId) {
					await createOrLoadCourseChat(courseId);
					return null;
				}
			} catch (e) {
				console.warn('createOrLoadCourseChat fallback failed', e);
			}

			// Friendly UI feedback instead of noisy console errors
			console.warn('loadChat failed, falling back to initNewChat', error);
			try { if (toast && typeof toast === 'function') toast({ message: 'Failed to load chat, starting a new session', type: 'warning', timeout: 3000 }); } catch {}
			await initNewChat();
			return null;
		}

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
				chatFiles = chatContent?.files ?? [];

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

<div id="chat-container" class="min-h-[calc(100vh-4rem)] w-full flex flex-col bg-transparent" style="font-family: Helvetica, Arial, sans-serif;">
  {#if !loading}
    <div class="flex-1 flex flex-col">
      <div class="w-full max-w-[1100px] mx-auto h-full px-4 md:px-6">
        <div class="flex h-full w-full">
          {#if showLeftPanel}
            <aside class="hidden md:block w-72 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 overflow-auto" aria-label="Course left panel">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-sm font-semibold uppercase tracking-wide">Sections</h3>
                <button class="text-xs px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" aria-label="Hide panel" on:click={hideLeftPanel}>
                  Hide
                </button>
              </div>

              <nav class="space-y-2 text-sm" aria-label="Course sections">
                <button class="w-full text-left px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => { /* overview */ }}>
                  Overview
                </button>
                <button class="w-full text-left px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => { /* materials */ }}>
                  Materials
                </button>
                <button class="w-full text-left px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => { /* assignments */ }}>
                  Assignments
                </button>
                <button class="w-full text-left px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => { /* virtual */ }}>
                  Virtual Classroom
                </button>
              </nav>

              <div class="mt-4 text-sm text-neutral-500">Overview</div>
              <div class="mt-1 text-sm text-neutral-400 line-clamp-3"><!-- dynamic overview content could go here --></div>
            </aside>
          {/if}

          <main class="flex-1 flex flex-col">
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

            <div class="flex-1 flex flex-col overflow-hidden">
              <div id="messages-container" bind:this={messagesContainerElement} class="flex-1 overflow-auto pb-2.5">
                <Messages
                  chatId={$chatId}
                  bind:history
                  bind:autoScroll
                  bind:prompt
                  setInputText={(text) => { messageInput?.setText(text); }}
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

              <div class="pt-2">
                <MessageInput
                  bind:this={messageInput}
                  bind:prompt
                  bind:autoScroll
                  bind:codeInterpreterEnabled
                  bind:atSelectedModel
                  on:submit={async (e) => {
                    if (e.detail) {
                      await tick();
                      submitPrompt(($settings?.richTextInput ?? true) ? e.detail.replaceAll('\n\n','\n') : e.detail);
                    }
                  }}
                  transparentBackground={$settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url ?? false}
                  onChange={(input) => {
                    if (!$temporaryChatEnabled && browser) {
                      if (input.prompt !== null) {
                        sessionStorage.setItem(`chat-input${$chatId ? `-${$chatId}` : ''}`, JSON.stringify(input));
                      } else {
                        sessionStorage.removeItem(`chat-input${$chatId ? `-${$chatId}` : ''}`);
                      }
                    }
                  }}
                />

                <div class="text-center text-xs text-gray-500 mt-2"> </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  {:else}
    <div class="flex items-center justify-center h-full w-full">
      <Spinner className="size-5" />
    </div>
  {/if}
</div>
