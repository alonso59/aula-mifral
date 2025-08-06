<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	
	const i18n = getContext('i18n');

	let submissions = [];
	let selectedSubmission = null;
	let showSubmissionModal = false;

	// Mock data for student submissions
	onMount(() => {
		submissions = [
			{
				id: 1,
				studentName: 'John Doe',
				submissionDate: '2024-01-22T10:30:00Z',
				type: 'verilog-code',
				title: 'ALU Implementation',
				status: 'pending',
				content: `module alu(
	input [3:0] a, b,
	input [1:0] op,
	output reg [3:0] result
);
always @(*) begin
	case(op)
		2'b00: result = a + b;
		2'b01: result = a - b;
		2'b10: result = a & b;
		2'b11: result = a | b;
	endcase
end
endmodule`
			},
			{
				id: 2,
				studentName: 'Jane Smith',
				submissionDate: '2024-01-22T14:15:00Z',
				type: 'text-answer',
				title: 'Verification Strategy',
				status: 'reviewed',
				content: 'My verification approach would include directed tests for each ALU operation, constrained random testing for edge cases, and functional coverage to ensure all operations are tested...',
				feedback: 'Good approach! Consider adding more details about coverage metrics and assertion-based verification.'
			},
			{
				id: 3,
				studentName: 'Mike Johnson',
				submissionDate: '2024-01-22T16:45:00Z',
				type: 'verilog-code',
				title: 'Testbench for Counter',
				status: 'needs-revision',
				content: `module counter_tb;
reg clk, rst;
wire [7:0] count;

counter dut(.clk(clk), .rst(rst), .count(count));

initial begin
	clk = 0;
	forever #5 clk = ~clk;
end

initial begin
	rst = 1;
	#10 rst = 0;
	#100 $finish;
end
endmodule`,
				feedback: 'Missing proper stimulus and checking. Add assertions and more comprehensive test scenarios.'
			}
		];
	});

	const getStatusColor = (status) => {
		switch (status) {
			case 'pending':
				return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
			case 'reviewed':
				return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
			case 'needs-revision':
				return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
			default:
				return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
		}
	};

	const getStatusIcon = (status) => {
		switch (status) {
			case 'pending':
				return '⏳';
			case 'reviewed':
				return '✅';
			case 'needs-revision':
				return '🔄';
			default:
				return '📄';
		}
	};

	const getTypeIcon = (type) => {
		switch (type) {
			case 'verilog-code':
				return '💻';
			case 'text-answer':
				return '📝';
			default:
				return '📄';
		}
	};

	const viewSubmission = (submission) => {
		selectedSubmission = submission;
		showSubmissionModal = true;
	};

	const updateSubmissionStatus = (submissionId, newStatus, feedback = '') => {
		submissions = submissions.map(sub => 
			sub.id === submissionId 
				? { ...sub, status: newStatus, feedback: feedback || sub.feedback }
				: sub
		);
		showSubmissionModal = false;
	};

	const formatDate = (dateString) => {
		return new Date(dateString).toLocaleString();
	};
</script>

<div class="space-y-4">
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-medium text-gray-900 dark:text-white">
			{$i18n.t('Student Submissions')}
		</h3>
		<span class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
			{submissions.filter(s => s.status === 'pending').length} {$i18n.t('pending')}
		</span>
	</div>

	<!-- Submissions List -->
	<div class="space-y-2 max-h-80 overflow-y-auto">
		{#if submissions.length === 0}
			<div class="text-center py-6 text-gray-500 dark:text-gray-400">
				<div class="text-3xl mb-2">📝</div>
				<p class="text-sm">{$i18n.t('No submissions yet')}</p>
			</div>
		{:else}
			{#each submissions as submission}
				<div
					class="p-3 border border-gray-200 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
					on:click={() => viewSubmission(submission)}
					role="button"
					tabindex="0"
					on:keydown={(e) => e.key === 'Enter' && viewSubmission(submission)}
				>
					<div class="flex items-start space-x-3">
						<div class="text-lg flex-shrink-0 mt-0.5">
							{getTypeIcon(submission.type)}
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center justify-between mb-1">
								<h4 class="text-sm font-medium text-gray-900 dark:text-white truncate">
									{submission.title}
								</h4>
								<span class="text-xs px-2 py-1 rounded-full {getStatusColor(submission.status)} flex items-center space-x-1">
									<span>{getStatusIcon(submission.status)}</span>
									<span>{$i18n.t(submission.status)}</span>
								</span>
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">
								<div class="flex items-center justify-between">
									<span>{submission.studentName}</span>
									<span>{formatDate(submission.submissionDate)}</span>
								</div>
							</div>
							{#if submission.feedback}
								<div class="mt-1 text-xs text-blue-600 dark:text-blue-400 truncate">
									💬 {submission.feedback}
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>

<!-- Submission Review Modal -->
{#if showSubmissionModal && selectedSubmission}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
			<!-- Modal Header -->
			<div class="p-6 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<div>
						<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
							{selectedSubmission.title}
						</h3>
						<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
							{$i18n.t('Submitted by')} {selectedSubmission.studentName} • {formatDate(selectedSubmission.submissionDate)}
						</p>
					</div>
					<button
						on:click={() => showSubmissionModal = false}
						class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>

			<!-- Modal Content -->
			<div class="p-6 space-y-4">
				<!-- Submission Content -->
				<div>
					<h4 class="text-sm font-medium text-gray-900 dark:text-white mb-2">
						{$i18n.t('Submission Content')}
					</h4>
					<div class="bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
						{#if selectedSubmission.type === 'verilog-code'}
							<pre class="text-sm font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap overflow-x-auto">{selectedSubmission.content}</pre>
						{:else}
							<p class="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{selectedSubmission.content}</p>
						{/if}
					</div>
				</div>

				<!-- Current Feedback -->
				{#if selectedSubmission.feedback}
					<div>
						<h4 class="text-sm font-medium text-gray-900 dark:text-white mb-2">
							{$i18n.t('Current Feedback')}
						</h4>
						<div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-md">
							<p class="text-sm text-blue-800 dark:text-blue-200">{selectedSubmission.feedback}</p>
						</div>
					</div>
				{/if}

				<!-- Feedback Form -->
				<div>
					<h4 class="text-sm font-medium text-gray-900 dark:text-white mb-2">
						{$i18n.t('Provide Feedback')}
					</h4>
					<textarea
						class="w-full h-24 p-3 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						placeholder={$i18n.t('Enter your feedback here...')}
						value={selectedSubmission.feedback || ''}
					></textarea>
				</div>
			</div>

			<!-- Modal Actions -->
			<div class="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
				<button
					on:click={() => showSubmissionModal = false}
					class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					on:click={() => updateSubmissionStatus(selectedSubmission.id, 'needs-revision')}
					class="px-4 py-2 text-sm bg-orange-600 hover:bg-orange-700 text-white rounded-md"
				>
					{$i18n.t('Request Revision')}
				</button>
				<button
					on:click={() => updateSubmissionStatus(selectedSubmission.id, 'reviewed')}
					class="px-4 py-2 text-sm bg-green-600 hover:bg-green-700 text-white rounded-md"
				>
					{$i18n.t('Approve')}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	pre {
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
	}
</style>

