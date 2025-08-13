<script lang="ts">
  // Intentionally disabled per UI/UX refactor: the Classroom right rail (Create / Workspace)
  // is removed from the default classroom runtime view. This component is kept as a
  // placeholder to avoid import errors elsewhere but renders nothing.
  export let open = false;
  export let course: any = null;
</script>

<!-- Right panel removed as part of the modernized classroom two-pane focus view. -->
<!-- If you need to restore this UI later, replace this file with the original implementation. -->
<div aria-hidden="true" style="display:none"></div>
