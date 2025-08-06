<script>
  import { user } from '$lib/stores';
  let isTeacher = $user.role === 'teacher';

  // TODO: Reemplazar con consulta a backend en producción
  let materials = [
    { title: 'Introducción a la IA', url: '/materials/intro.pdf' },
    { title: 'Algoritmos básicos', url: '/materials/algos.pdf' }
  ];

  function uploadMaterial() {
    // TODO: Implementar lógica real de subida de PDF para docentes
    alert("Funcionalidad para subir PDFs (solo docentes)");
  }
  function giveInstructions() {
    // TODO: Implementar lógica real para dar instrucciones al modelo
    alert("Funcionalidad para dar instrucciones al modelo (solo docentes)");
  }
</script>

{#if isTeacher}
  <button on:click={uploadMaterial}>Subir PDF</button>
  <button on:click={giveInstructions}>Dar instrucciones al modelo</button>
{/if}

<h2>Material educativo</h2>
<ul>
  {#each materials as material}
    <li><a href={material.url} target="_blank">{material.title}</a></li>
  {/each}
</ul>

<!-- Chat con IA sobre el material -->
<!-- Reemplazar ChatComponent por el componente real de chat -->
<!-- <ChatComponent context={materials} /> -->
