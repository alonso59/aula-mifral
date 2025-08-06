<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, WEBUI_NAME } from '$lib/stores';
	
	const i18n = getContext('i18n');

	const handleCreateCourse = () => {
		goto('/admin/courses/new');
	};

	const handleJoinCourse = () => {
		goto('/courses/join');
	};

	const handleStartChat = () => {
		goto('/');
	};

	const getWelcomeMessage = () => {
		const role = $user?.role;
		switch (role) {
			case 'admin':
				return $i18n.t('Welcome to {{WEBUI_NAME}}! As an administrator, you can create and manage courses, users, and system settings.', { WEBUI_NAME: $WEBUI_NAME });
			case 'teacher':
				return $i18n.t('Welcome to {{WEBUI_NAME}}! As a teacher, you can create courses, manage students, and facilitate learning.', { WEBUI_NAME: $WEBUI_NAME });
			case 'student':
				return $i18n.t('Welcome to {{WEBUI_NAME}}! As a student, you can join courses, participate in discussions, and access learning materials.', { WEBUI_NAME: $WEBUI_NAME });
			default:
				return $i18n.t('Welcome to {{WEBUI_NAME}}! Get started by exploring our features.', { WEBUI_NAME: $WEBUI_NAME });
		}
	};

	const getAvailableActions = () => {
		const role = $user?.role;
		const actions = [];

		if (role === 'admin' || role === 'teacher') {
			actions.push({
				title: $i18n.t('Create Course'),
				description: $i18n.t('Start by creating your first course'),
				action: handleCreateCourse,
				primary: true
			});
		}

		if (role === 'student' || role === 'teacher') {
			actions.push({
				title: $i18n.t('Join Course'),
				description: $i18n.t('Find and join available courses'),
				action: handleJoinCourse,
				primary: role === 'student'
			});
		}

		actions.push({
			title: $i18n.t('Start Chatting'),
			description: $i18n.t('Begin a conversation with AI'),
			action: handleStartChat,
			primary: false
		});

		if (role === 'admin') {
			actions.push({
				title: $i18n.t('Manage Users'),
				description: $i18n.t('Add and manage system users'),
				action: () => goto('/admin'),
				primary: false
			});
		}

		return actions;
	};
</script>

<div class="w-full h-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
	<div class="max-w-4xl mx-auto px-6 py-12 text-center">
		<!-- Welcome Header -->
		<div class="mb-12">
			<h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">
				{$i18n.t('Welcome to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
			</h1>
			<p class="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
				{getWelcomeMessage()}
			</p>
		</div>

		<!-- Action Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
			{#each getAvailableActions() as action}
				<button
					class="p-6 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 
					       bg-white dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-gray-700 
					       transition-all duration-200 text-left group
					       {action.primary ? 'ring-2 ring-blue-500 dark:ring-blue-400' : ''}"
					on:click={action.action}
				>
					<div class="flex items-center mb-4">
						<div class="p-3 rounded-lg bg-blue-100 dark:bg-blue-900 group-hover:bg-blue-200 dark:group-hover:bg-blue-800 transition-colors">
							<div class="w-6 h-6 text-blue-600 dark:text-blue-400">
								{#if action.title.includes('Create')}
									<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
									</svg>
								{:else if action.title.includes('Join') || action.title.includes('Course')}
									<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
									</svg>
								{:else if action.title.includes('Chat')}
									<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
									</svg>
								{:else}
									<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
									</svg>
								{/if}
							</div>
						</div>
					</div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
						{action.title}
					</h3>
					<p class="text-gray-600 dark:text-gray-300 text-sm">
						{action.description}
					</p>
					{#if action.primary}
						<div class="mt-3 text-xs font-medium text-blue-600 dark:text-blue-400">
							{$i18n.t('Recommended')}
						</div>
					{/if}
				</button>
			{/each}
		</div>

		<!-- Quick Start Guide -->
		<div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8">
			<h2 class="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
				{$i18n.t('Quick Start Guide')}
			</h2>
			
			<div class="space-y-4 text-left">
				{#if $user?.role === 'admin'}
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Set up your system')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Configure models, create user accounts, and set up courses.')}</p>
						</div>
					</div>
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Create your first course')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Design learning experiences and invite students to participate.')}</p>
						</div>
					</div>
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Monitor and support')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Track usage, manage user accounts, and provide technical support.')}</p>
						</div>
					</div>
				{:else if $user?.role === 'teacher'}
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Create your course')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Set up course materials, objectives, and structure.')}</p>
						</div>
					</div>
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Invite students')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Add students to your course and begin teaching.')}</p>
						</div>
					</div>
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Facilitate learning')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Guide discussions, provide feedback, and track progress.')}</p>
						</div>
					</div>
				{:else if $user?.role === 'student'}
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Join a course')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Find courses available to you and enroll.')}</p>
						</div>
					</div>
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Explore materials')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Access course content and learning resources.')}</p>
						</div>
					</div>
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white">{$i18n.t('Participate and learn')}</h4>
							<p class="text-gray-600 dark:text-gray-300 text-sm">{$i18n.t('Engage in discussions, complete assignments, and ask questions.')}</p>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Footer -->
		<div class="mt-8 text-center">
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Need help? Check the documentation or contact support.')}
			</p>
		</div>
	</div>
</div>

