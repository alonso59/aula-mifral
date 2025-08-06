<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { selectedCourse, showDocumentPanel } from '$lib/stores';
	import Chat from '$lib/components/chat/Chat.svelte';

	const i18n = getContext('i18n');

	export let data;

	onMount(() => {
		// Set the current course in the store
		selectedCourse.set(data.course);
		
		// Ensure document panel is shown for course context
		showDocumentPanel.set(true);
	});
</script>

<svelte:head>
	<title>{data.course.name} - Course Chat</title>
</svelte:head>

<!-- Use the existing Chat component but with course context -->
<Chat chatIdProp="" courseId={data.courseId} />
