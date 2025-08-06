<script>
	export let data;
</script>

<svelte:head>
	<title>Course Chat</title>
</svelte:head>

<div class="h-screen w-screen flex">
	<!-- This will use the existing Chat component but in course context -->
	<slot />
</div>
