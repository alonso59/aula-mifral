export interface Course {
	id: string;
	name: string;
	description?: string;
	teacher_id: string;
	created_at: number;
	updated_at: number;
}

export interface CourseDocument {
	id: string;
	course_id: string;
	file_id: string;
	name: string;
	mime_type?: string;
	embed_status: string;
	created_at: number;
	updated_at: number;
}

export interface Enrollment {
	id: string;
	course_id: string;
	user_id: string;
	role: 'student' | 'teacher';
	created_at: number;
}

export interface StudentFeedback {
	id: string;
	course_id: string;
	user_id: string;
	task_id: string;
	feedback: string;
	rating?: number;
	created_at: number;
	updated_at: number;
}

