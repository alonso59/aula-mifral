import { redirect } from '@sveltejs/kit';
export const load = ({ params }) => {
  throw redirect(307, `/classroom/${params.courseId}/overview`);
};