<script lang="ts">
	import { getContext } from 'svelte';
	
	const i18n = getContext('i18n');

	export let courseData = {};

	const getStatusIcon = (status) => {
		switch (status) {
			case 'completed':
				return '✅';
			case 'in-progress':
				return '🔄';
			case 'pending':
				return '⏳';
			default:
				return '📋';
		}
	};

	const getStatusColor = (status) => {
		switch (status) {
			case 'completed':
				return 'text-green-600 dark:text-green-400';
			case 'in-progress':
				return 'text-blue-600 dark:text-blue-400';
			case 'pending':
				return 'text-gray-500 dark:text-gray-400';
			default:
				return 'text-gray-600 dark:text-gray-300';
		}
	};
</script>

<div class="space-y-4">
	<!-- Course Title and Description -->
	<div>
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
			{courseData.title || $i18n.t('Digital Design Course')}
		</h3>
		<p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
			{courseData.description || $i18n.t('Learn digital design fundamentals with Verilog')}
		</p>
	</div>

	<!-- Course Progress -->
	{#if courseData.modules && courseData.modules.length > 0}
		<div>
			<h4 class="text-sm font-medium text-gray-900 dark:text-white mb-3">
				{$i18n.t('Course Modules')}
			</h4>
			<div class="space-y-2">
				{#each courseData.modules as module, index}
					<div class="flex items-center space-x-3 p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-600 flex items-center justify-center text-xs font-medium">
							{index + 1}
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center justify-between">
								<span class="text-sm font-medium text-gray-900 dark:text-white truncate">
									{module.name}
								</span>
								<div class="flex items-center space-x-1">
									<span class="text-sm {getStatusColor(module.status)}">
										{getStatusIcon(module.status)}
									</span>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Progress Bar -->
		<div>
			<div class="flex items-center justify-between mb-2">
				<span class="text-sm font-medium text-gray-900 dark:text-white">
					{$i18n.t('Overall Progress')}
				</span>
				<span class="text-sm text-gray-600 dark:text-gray-300">
					{Math.round((courseData.modules.filter(m => m.status === 'completed').length / courseData.modules.length) * 100)}%
				</span>
			</div>
			<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
				<div 
					class="bg-blue-600 h-2 rounded-full transition-all duration-300"
					style="width: {(courseData.modules.filter(m => m.status === 'completed').length / courseData.modules.length) * 100}%"
				></div>
			</div>
		</div>
	{/if}

	<!-- Course Statistics -->
	<div class="grid grid-cols-2 gap-3">
		<div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-md">
			<div class="text-sm font-medium text-blue-900 dark:text-blue-200">
				{$i18n.t('Completed')}
			</div>
			<div class="text-lg font-bold text-blue-600 dark:text-blue-400">
				{courseData.modules?.filter(m => m.status === 'completed').length || 0}
			</div>
		</div>
		<div class="bg-orange-50 dark:bg-orange-900/20 p-3 rounded-md">
			<div class="text-sm font-medium text-orange-900 dark:text-orange-200">
				{$i18n.t('Remaining')}
			</div>
			<div class="text-lg font-bold text-orange-600 dark:text-orange-400">
				{courseData.modules?.filter(m => m.status !== 'completed').length || 0}
			</div>
		</div>
	</div>

	<!-- Quick Actions -->
	<div class="pt-2 border-t border-gray-200 dark:border-gray-700">
		<h4 class="text-sm font-medium text-gray-900 dark:text-white mb-2">
			{$i18n.t('Quick Actions')}
		</h4>
		<div class="space-y-2">
			<button class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors">
				📈 {$i18n.t('View Progress Report')}
			</button>
			<button class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors">
				💡 {$i18n.t('Get Learning Tips')}
			</button>
			<button class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors">
				🎯 {$i18n.t('Set Learning Goals')}
			</button>
		</div>
	</div>
</div>

