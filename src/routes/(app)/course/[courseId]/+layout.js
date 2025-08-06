import { getCourseById } from '$lib/apis/courses';
import { error } from '@sveltejs/kit';

export async function load({ params, url, parent }) {
	const { user } = await parent();
	
	if (!user) {
		throw error(401, 'Unauthorized');
	}

	try {
		const course = await getCourseById(user.token, params.courseId);
		
		if (!course) {
			throw error(404, 'Course not found');
		}

		return {
			course,
			courseId: params.courseId
		};
	} catch (e) {
		console.error('Error loading course:', e);
		throw error(500, 'Failed to load course');
	}
}
