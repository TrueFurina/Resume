import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// ---- 类型定义 ----
export interface ScheduleStatus {
  loaded: boolean;
  total_entries: number;
  rooms: string[];
  teachers: string[];
  week_range: number[];
}

export interface AvailableSlot {
  weekday: string;
  time_slot: string;
  room: string;
  date?: string;
}

export interface ChatResponse {
  success: boolean;
  message: string;
  data: {
    target_week?: number;
    available_slots?: AvailableSlot[];
    excluded_slots?: ExcludedSlot[];
    total?: number;
    need_info?: boolean;
    followup_questions?: string[];
  };
}

export interface UploadResponse {
  success: boolean;
  message: string;
  total_entries: number;
  rooms: string[];
  teachers: string[];
  week_range: number[];
}

export interface StudentStatus {
  name: string;
  student_id: string;
  semester: string;
  total_courses: number;
  sample_courses: [string, string, string, string][];
}

export interface Teacher {
  name: string;
  title: string;
}

export interface TeacherCourse {
  course_name: string;
  class_name: string;
  original_time: string;
  room: string;
  week_range: string;
  total_slots: number;
  adjustable: boolean;
  adjustable_reason: string;
}

export interface ExcludedSlot {
  weekday: string;
  time_slot: string;
  room: string;
  date?: string;
  reason_type: string;
  reason: string;
}

export interface RescheduleRequest {
  id: number;
  teacher: string;
  course_name: string;
  class_name: string;
  original_time: string;
  target_week: number;
  reason: string;
  status: string;  // pending / approved / rejected
  admin_comment: string;
  created_at: string;
}

// ---- API 函数 ----
export const rescheduleApi = {
  // 获取状态
  getStatus: () => api.get<ScheduleStatus>('/reschedule/status'),

  // 加载默认数据
  loadDefault: () => api.post<{ success: boolean; message: string; total_entries: number }>('/reschedule/load-default'),

  // 上传文件
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<UploadResponse>('/reschedule/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // 上传学生课表
  uploadStudent: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<{ success: boolean; message: string; total_courses: number }>('/reschedule/upload-student', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // 学生课表状态
  getStudentStatus: () => api.get<StudentStatus>('/reschedule/student-status'),

  // 教师列表（F1 身份选择）
  getTeachers: () => api.get<{ success: boolean; teachers: Teacher[]; total: number }>('/reschedule/teachers'),

  // 教师课程列表（F2）
  getTeacherCourses: (teacherName: string) =>
    api.get<{ success: boolean; teacher: string; courses: TeacherCourse[]; total: number }>(`/reschedule/teachers/${encodeURIComponent(teacherName)}/courses`),

  // 调课咨询
  chat: (message: string) =>
    api.post<ChatResponse>('/reschedule/chat', { message }),

  // 提交调课申请（F6）
  createRequest: (data: {
    teacher: string; course_name: string; class_name: string;
    original_time: string; target_week: number; reason: string;
  }) => api.post<{ success: boolean; message: string; request: RescheduleRequest }>('/reschedule/requests', data),

  // 申请列表（F6）
  listRequests: (status?: string) =>
    api.get<{ success: boolean; requests: RescheduleRequest[]; total: number }>('/reschedule/requests', { params: status ? { status } : {} }),

  // 管理员审批（F6）
  approveRequest: (id: number, approve: boolean, comment: string) =>
    api.post<{ success: boolean; message: string; request: RescheduleRequest }>(`/reschedule/requests/${id}/approve`, { approve, comment }),

  // 选课咨询（四大模块之一）
  courseSelect: (question: string) =>
    api.post<{ success: boolean; message: string; reply: string }>('/reschedule/course-select', { question }),

  // 实验辅导（四大模块之一）
  experimentTutor: (question: string) =>
    api.post<{ success: boolean; message: string; reply: string }>('/reschedule/experiment-tutor', { question }),

  // 排课自动生成（P1）
  autoSchedule: () =>
    api.post<{ success: boolean; message: string; data: {
      total_sections: number; solved: number; conflicts: any[]; schedule: any[];
    } }>('/reschedule/auto-schedule'),

  // 管理员登录（审批台）
  adminLogin: (username: string, password: string) =>
    api.post<{ success: boolean; message: string; role: string }>('/reschedule/admin-login', { username, password }),
};
