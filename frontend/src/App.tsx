import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  rescheduleApi, Teacher, TeacherCourse, AvailableSlot, ExcludedSlot, RescheduleRequest,
} from './api/client';

const weekdayLabels: Record<string, string> = {
  '周一': '周一', '周二': '周二', '周三': '周三',
  '周四': '周四', '周五': '周五', '周六': '周六', '周日': '周日',
};

const timeSlotLabels: Record<string, string> = {
  '567': '13:30-15:45',
  '678': '15:45-18:00',
  '91011': '18:30-20:45',
  '78': '15:50-18:05',
};

type View = 'identity' | 'courses' | 'reschedule' | 'admin' | 'course_select' | 'tutor';

function App() {
  const [view, setView] = useState<View>('identity');
  const [module, setModule] = useState('');  // 当前咨询模块: course_select / tutor
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [currentTeacher, setCurrentTeacher] = useState<string>('');
  const [courses, setCourses] = useState<TeacherCourse[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<TeacherCourse | null>(null);
  const [available, setAvailable] = useState<AvailableSlot[]>([]);
  const [excluded, setExcluded] = useState<ExcludedSlot[]>([]);
  const [showAllAvail, setShowAllAvail] = useState(false);  // 可用时段展开更多
  const [targetWeek, setTargetWeek] = useState(2);  // 模板表单：目标周次
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [dataLoaded, setDataLoaded] = useState(false);
  const [requestStatus, setRequestStatus] = useState('');  // 申请提交后的状态反馈
  const [requests, setRequests] = useState<RescheduleRequest[]>([]);  // 审批台申请列表
  const [nlInput, setNlInput] = useState('');  // 自然语言调课输入
  const [followupQ, setFollowupQ] = useState<string[]>([]);  // 多轮追问问题
  const [nlMsg, setNlMsg] = useState('');  // 自然语言反馈消息
  const [consultQ, setConsultQ] = useState('');  // 选课/辅导咨询输入
  const [consultMsg, setConsultMsg] = useState('');  // 咨询回复
  const [autoScheduleMsg, setAutoScheduleMsg] = useState('');  // 自动排课结果
  const [autoScheduleLoading, setAutoScheduleLoading] = useState(false);  // 自动排课中
  const [showAdminLogin, setShowAdminLogin] = useState(false);  // 管理员登录弹窗
  const [adminAuthed, setAdminAuthed] = useState(false);  // 管理员是否已登录
  const [adminUser, setAdminUser] = useState('');  // 管理员账号
  const [adminPass, setAdminPass] = useState('');  // 管理员密码
  const [adminLoginErr, setAdminLoginErr] = useState('');  // 登录错误

  // P1: 排课自动生成
  const handleAutoSchedule = async () => {
    setAutoScheduleLoading(true);
    setAutoScheduleMsg('');
    try {
      const r = await rescheduleApi.autoSchedule();
      setAutoScheduleMsg(r.data.message);
    } catch (err: any) {
      setAutoScheduleMsg(`❌ 自动排课失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setAutoScheduleLoading(false);
    }
  };

  // 四大模块：选课咨询 / 实验辅导（LLM 咨询）
  const handleConsult = async () => {
    const q = consultQ.trim();
    if (!q) return;
    setLoading(true);
    setConsultMsg('');
    try {
      const r = module === 'course_select'
        ? await rescheduleApi.courseSelect(q)
        : await rescheduleApi.experimentTutor(q);
      setConsultMsg(r.data.reply || r.data.message);
    } catch (err: any) {
      setConsultMsg(`❌ 请求失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
      setConsultQ('');
    }
  };

  // 打开选课咨询 / 实验辅导模块
  const handleOpenModule = (m: string) => {
    setModule(m);
    setConsultMsg('');
    setConsultQ('');
    setView(m === 'course_select' ? 'course_select' : 'tutor');
  };

  // 进入时自动加载默认数据
  useEffect(() => {
    const init = async () => {
      try {
        await rescheduleApi.loadDefault();
        const t = await rescheduleApi.getTeachers();
        setTeachers(t.data.teachers);
        setDataLoaded(true);
      } catch (err: any) {
        setMsg(`加载失败：${err.response?.data?.detail || err.message}`);
      }
    };
    init();
  }, []);

  // F1: 选择教师身份 → 加载其课程列表（F2）
  const handleSelectTeacher = async (name: string) => {
    setLoading(true);
    try {
      const r = await rescheduleApi.getTeacherCourses(name);
      setCourses(r.data.courses);
      setCurrentTeacher(name);
      setSelectedCourse(null);
      setAvailable([]);
      setExcluded([]);
      setView('courses');
    } catch (err: any) {
      setMsg(`加载课程失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // F3/F4: 模板表单选择课程 + 目标周次 → 查询可用时段（含原因标注）
  const handleReschedule = async (course: TeacherCourse, week?: number) => {
    setSelectedCourse(course);
    setLoading(true);
    try {
      const target = week ?? targetWeek;
      const r = await rescheduleApi.chat(
        `我是${currentTeacher}，把${course.course_name}调到第${target}周`
      );
      setAvailable(r.data.data.available_slots || []);
      setExcluded(r.data.data.excluded_slots || []);
      setView('reschedule');
    } catch (err: any) {
      setMsg(`查询失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 模板表单：更改目标周次后重新查询
  const handleTargetWeekChange = (week: number) => {
    setTargetWeek(week);
    if (selectedCourse) {
      handleReschedule(selectedCourse, week);
    }
  };

  // F6: 提交调课申请
  const handleSubmitRequest = async () => {
    if (!selectedCourse) return;
    setLoading(true);
    try {
      const r = await rescheduleApi.createRequest({
        teacher: currentTeacher,
        course_name: selectedCourse.course_name,
        class_name: selectedCourse.class_name,
        original_time: `${selectedCourse.original_time} · ${selectedCourse.room}`,
        target_week: targetWeek,
        reason: '调课申请',
      });
      setRequestStatus(r.data.message);
    } catch (err: any) {
      setMsg(`提交失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // B1/B2: 自然语言调课（支持多轮追问——信息缺失时系统追问）
  const handleNlReschedule = async () => {
    const text = nlInput.trim();
    if (!text) return;
    setLoading(true);
    setNlMsg('');
    try {
      const r = await rescheduleApi.chat(text);
      const data = r.data.data;
      // 需要追问（信息缺失）
      if (data.need_info && data.followup_questions?.length) {
        setFollowupQ(data.followup_questions);
        setNlMsg(`🤔 ${r.data.message}`);
        return;
      }
      setFollowupQ([]);
      // 有可用时段 → 展示结果
      if (data.available_slots?.length) {
        setAvailable(data.available_slots);
        setExcluded(data.excluded_slots || []);
        setNlMsg(`✅ ${r.data.message.split('\n')[0]}`);
        setView('reschedule');
        return;
      }
      setNlMsg(r.data.message);
    } catch (err: any) {
      setNlMsg(`❌ 请求失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
      setNlInput('');
    }
  };

  // 返回身份选择
  const handleBackToIdentity = () => {
    setView('identity');
    setCurrentTeacher('');
    setCourses([]);
  };

  // F6: 管理员进入审批台（需登录验证，普通用户免登录）
  const handleOpenAdmin = async () => {
    if (!adminAuthed) {
      setShowAdminLogin(true);  // 未登录 → 弹登录框
      return;
    }
    setLoading(true);
    try {
      const r = await rescheduleApi.listRequests('pending');
      setRequests(r.data.requests);
      setView('admin');
    } catch (err: any) {
      setMsg(`加载审批列表失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 管理员登录提交
  const handleAdminLogin = async () => {
    setLoading(true);
    setAdminLoginErr('');
    try {
      await rescheduleApi.adminLogin(adminUser, adminPass);
      setAdminAuthed(true);
      setShowAdminLogin(false);
      const lst = await rescheduleApi.listRequests('pending');
      setRequests(lst.data.requests);
      setView('admin');
    } catch (err: any) {
      setAdminLoginErr(err.response?.data?.detail || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  // F6: 管理员审批（同意/驳回）
  const handleApprove = async (id: number, approve: boolean, comment: string) => {
    setLoading(true);
    try {
      await rescheduleApi.approveRequest(id, approve, comment);
      // 刷新待审批列表
      const r = await rescheduleApi.listRequests('pending');
      setRequests(r.data.requests);
    } catch (err: any) {
      setMsg(`审批失败：${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">物理实验调课辅助</h1>
            <p className="text-sm text-gray-500">先选身份 → 看我的课程 → 调课</p>
          </div>
          {view !== 'identity' && (
            <button
              onClick={handleBackToIdentity}
              className="text-sm px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              ← 返回身份选择
            </button>
          )}
        </div>

        {/* 步骤指示器（评审：缺少用户引导） */}
        <div className="max-w-4xl mx-auto px-4 pb-3">
          <div className="flex items-center gap-1 text-xs">
            {[
              { key: 'identity', label: '① 选择身份' },
              { key: 'courses', label: '② 我的课程' },
              { key: 'reschedule', label: '③ 选择时间' },
              { key: 'admin', label: '④ 管理员审批' },
            ].map((s, i) => (
              <div key={s.key} className="flex items-center gap-1">
                {i > 0 && <span className="text-gray-300">›</span>}
                <span
                  className={`px-2 py-1 rounded-full ${
                    (view === s.key) || (view === 'reschedule' && s.key === 'reschedule')
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-400'
                  }`}
                >
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 四大模块导航（排课/选课/调课/辅导） */}
        <div className="max-w-4xl mx-auto px-4 pb-3">
          <div className="flex items-center gap-2 text-sm">
            <button
              onClick={() => setView('identity')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                ['identity', 'courses', 'reschedule'].includes(view) && !['course_select', 'tutor', 'admin'].includes(view)
                  ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              📅 排课调课
            </button>
            <button
              onClick={() => handleOpenModule('course_select')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                view === 'course_select' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              🎓 选课咨询
            </button>
            <button
              onClick={() => handleOpenModule('tutor')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                view === 'tutor' ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              🔬 实验辅导
            </button>
            <button
              onClick={handleOpenAdmin}
              className={`px-4 py-2 rounded-lg transition-colors ${
                view === 'admin' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              ⚙️ 审批
            </button>
          </div>
        </div>
      </header>

      {msg && (
        <div className="max-w-4xl mx-auto px-4 pt-3">
          <div className="bg-red-50 text-red-600 text-sm px-4 py-2.5 rounded-lg border border-red-200">
            {msg}
          </div>
        </div>
      )}

      {/* 管理员登录弹窗（F6：审批台需登录，普通用户免登录） */}
      {showAdminLogin && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">🔐 管理员登录</h3>
            <p className="text-sm text-gray-500 mb-4">进入审批台需要管理员身份验证</p>
            <div className="space-y-3">
              <input
                type="text"
                value={adminUser}
                onChange={(e) => setAdminUser(e.target.value)}
                placeholder="账号"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              />
              <input
                type="password"
                value={adminPass}
                onChange={(e) => setAdminPass(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAdminLogin()}
                placeholder="密码"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              />
              {adminLoginErr && (
                <div className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg">{adminLoginErr}</div>
              )}
              <div className="flex gap-2 pt-1">
                <button
                  onClick={handleAdminLogin}
                  disabled={loading}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
                >
                  {loading ? '登录中...' : '登录'}
                </button>
                <button
                  onClick={() => setShowAdminLogin(false)}
                  className="px-4 py-2.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 text-sm"
                >
                  取消
                </button>
              </div>
              <p className="text-xs text-gray-400 text-center pt-1">演示账号：admin / admin123</p>
            </div>
          </div>
        </div>
      )}

      <main className="max-w-4xl mx-auto p-4">
        {!dataLoaded && loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
            <div className="text-gray-400">⏳ 数据加载中...</div>
          </div>
        )}

        {/* 页面1：身份选择（F1） */}
        {view === 'identity' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">请选择您的身份（教师）</h2>
              <button
                onClick={handleOpenAdmin}
                className="text-sm px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                ⚙️ 管理员审批台
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-6">系统将展示您名下的全部课程与可调时段</p>

            {/* P1: 排课自动生成入口 */}
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">🤖 排课自动生成</h3>
                  <p className="text-sm text-gray-500 mt-1">基于约束求解器，自动生成完整排课方案（教室/教师/学生三重不冲突）</p>
                </div>
                <button
                  onClick={handleAutoSchedule}
                  disabled={autoScheduleLoading}
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition-colors shrink-0"
                >
                  {autoScheduleLoading ? '⏳ 排课中...' : '一键自动排课'}
                </button>
              </div>
              {autoScheduleMsg && (
                <div className="mt-4 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {autoScheduleMsg}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {teachers.map((t) => (
                <button
                  key={t.name}
                  onClick={() => handleSelectTeacher(t.name)}
                  className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 hover:border-blue-400 hover:shadow-md transition-all text-left"
                >
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-3">
                    <span className="text-blue-700 font-bold text-lg">{t.name[0]}</span>
                  </div>
                  <div className="font-semibold text-gray-900">{t.name}</div>
                  <div className="text-xs text-gray-500 mt-1">{t.title}</div>
                  <div className="text-xs text-blue-600 mt-3">进入我的课程 →</div>
                </button>
              ))}
            </div>
            {teachers.length === 0 && (
              <div className="text-center text-gray-400 py-16">暂无教师数据，请先加载实验安排表</div>
            )}
          </div>
        )}

        {/* 页面4：管理员审批台（F6） */}
        {view === 'admin' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">管理员审批台</h2>
              <button
                onClick={handleBackToIdentity}
                className="text-sm px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
              >
                ← 返回
              </button>
            </div>

            <div className="mb-4 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600">
              待审批申请：{requests.length} 条
            </div>

            {requests.length === 0 && (
              <div className="text-center text-gray-400 py-16">
                <p className="text-4xl mb-3">📭</p>
                <p>暂无待审批的调课申请</p>
                <p className="text-sm mt-2 text-gray-300">教师提交申请后会显示在这里</p>
              </div>
            )}

            <div className="space-y-4">
              {requests.map((r) => (
                <div key={r.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-200">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-gray-900">
                        {r.teacher} · {r.course_name}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">{r.class_name}</div>
                      <div className="text-sm text-gray-500 mt-1">
                        {r.original_time} → <span className="font-medium text-blue-600">第{r.target_week}周</span>
                      </div>
                      <div className="text-xs text-gray-400 mt-2">理由：{r.reason}</div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => handleApprove(r.id, true, '同意调课')}
                        disabled={loading}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
                      >
                        同意
                      </button>
                      <button
                        onClick={() => handleApprove(r.id, false, '时间冲突，请重新选择')}
                        disabled={loading}
                        className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 text-sm font-medium"
                      >
                        驳回
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 页面2：我的课程（F2） */}
        {view === 'courses' && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-700 font-bold">{currentTeacher[0]}</span>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">当前教师：{currentTeacher}</h2>
                <p className="text-sm text-gray-500">共 {courses.length} 门课程</p>
              </div>
            </div>

            {/* 可调课程 */}
            <h3 className="font-medium text-green-700 mb-3">✅ 可调课程</h3>
            <div className="space-y-3 mb-8">
              {courses.filter(c => c.adjustable).map((c, i) => (
                <div key={i} className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900">{c.course_name}</div>
                    <div className="text-sm text-gray-500 mt-1">{c.class_name}</div>
                    <div className="text-xs text-gray-400 mt-1">
                      {c.original_time} · {c.room} · {c.week_range}
                    </div>
                  </div>
                  <button
                    onClick={() => handleReschedule(c)}
                    className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors shrink-0"
                  >
                    申请调课 →
                  </button>
                </div>
              ))}
              {courses.filter(c => c.adjustable).length === 0 && (
                <div className="text-gray-400 text-sm text-center py-6">没有可调课程</div>
              )}
            </div>

            {/* 不可调课程 */}
            <h3 className="font-medium text-red-600 mb-3">❌ 不可调课程</h3>
            <div className="space-y-3">
              {courses.filter(c => !c.adjustable).map((c, i) => (
                <div key={i} className="bg-gray-50 rounded-xl p-4 border border-gray-200 opacity-80">
                  <div className="font-semibold text-gray-500">{c.course_name}</div>
                  <div className="text-sm text-gray-400 mt-1">{c.class_name}</div>
                  <div className="text-xs text-red-500 mt-2">
                    ⚠️ {c.adjustable_reason || '该课程不可调'}
                  </div>
                </div>
              ))}
              {courses.filter(c => !c.adjustable).length === 0 && (
                <div className="text-gray-400 text-sm text-center py-6">暂无不可调课程</div>
              )}
            </div>

            {/* B1/B2: 自然语言调课（多轮追问） */}
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 mt-8">
              <h3 className="font-medium text-gray-900 mb-1">💬 自然语言调课</h3>
              <p className="text-xs text-gray-400 mb-3">也可以直接说出需求，如"我是吴琳，下周三有事，把实验课往后挪一周"</p>
              <div className="flex gap-2">
                <input
                  value={nlInput}
                  onChange={(e) => setNlInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleNlReschedule()}
                  placeholder="输入大白话调课需求..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  disabled={loading}
                />
                <button
                  onClick={handleNlReschedule}
                  disabled={loading || !nlInput.trim()}
                  className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:opacity-50 text-sm font-medium"
                >
                  {loading ? '解析中...' : '发送'}
                </button>
              </div>

              {/* 多轮追问（B2：信息缺失时系统追问） */}
              {followupQ.length > 0 && (
                <div className="mt-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="text-sm font-medium text-amber-800 mb-2">🤔 需要补充信息</div>
                  {followupQ.map((q, i) => (
                    <div key={i} className="text-sm text-amber-700 ml-2">• {q}</div>
                  ))}
                  <p className="text-xs text-amber-500 mt-2">请在上方输入框补充回答，我会继续为您处理</p>
                </div>
              )}

              {/* 自然语言反馈 */}
              {nlMsg && (
                <div className="mt-3 text-sm text-gray-600 whitespace-pre-wrap">{nlMsg}</div>
              )}
            </div>
          </div>
        )}

        {/* 页面3：调课结果（F3/F4） */}
        {view === 'reschedule' && selectedCourse && (
          <div>
            <button
              onClick={() => setView('courses')}
              className="text-sm px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 mb-4"
            >
              ← 返回课程列表
            </button>

            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 mb-6">
              <h2 className="font-semibold text-gray-900">调课申请 · 模板表单</h2>
              <div className="text-sm text-gray-600 mt-2">
                课程：{selectedCourse.course_name}（{selectedCourse.class_name}）
              </div>
              <div className="text-sm text-gray-600 mt-1">
                原时间：{selectedCourse.original_time} · {selectedCourse.room} · {selectedCourse.week_range}
              </div>
              <div className="flex items-center gap-3 mt-4">
                <label className="text-sm text-gray-600">目标周次：</label>
                <select
                  value={targetWeek}
                  onChange={(e) => handleTargetWeekChange(Number(e.target.value))}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  {Array.from({ length: 16 }, (_, i) => i + 1).map(w => (
                    <option key={w} value={w}>第{w}周</option>
                  ))}
                </select>
                <span className="text-xs text-gray-400">（选择后自动重新查询可用时段）</span>
              </div>
            </div>

            {/* 可用时段 */}
            <h3 className="font-medium text-green-700 mb-3">✅ 可用时段（{available.length}）</h3>
            <div className="bg-white rounded-xl border border-green-200 mb-6 overflow-hidden">
              {available.length === 0 && (
                <div className="text-gray-400 text-sm text-center py-6">无可用时段</div>
              )}
              <div className="divide-y divide-gray-50">
                {(showAllAvail ? available : available.slice(0, 20)).map((s, i) => (
                  <div key={i} className="px-4 py-2.5 flex items-center text-sm">
                    <span className="text-green-600 mr-3">✅</span>
                    <span className="font-medium text-gray-800">{weekdayLabels[s.weekday]}</span>
                    {s.date && <span className="text-gray-500 ml-2">{s.date}</span>}
                    <span className="text-gray-500 ml-2">{timeSlotLabels[s.time_slot] || s.time_slot}</span>
                    <span className="text-gray-400 ml-3">{s.room}</span>
                  </div>
                ))}
              </div>
              {available.length > 20 && (
                <button
                  onClick={() => setShowAllAvail(!showAllAvail)}
                  className="w-full py-2.5 text-sm text-blue-600 hover:bg-blue-50 transition-colors border-t border-gray-100"
                >
                  {showAllAvail ? '收起 ▲' : `展开全部 ${available.length} 个时段 ▼`}
                </button>
              )}
            </div>

            {/* 被排除时段（含原因，F4） */}
            <h3 className="font-medium text-gray-600 mb-3">🚫 被排除时段（{excluded.length}）</h3>
            <div className="bg-white rounded-xl border border-gray-200 mb-6 overflow-hidden">
              {excluded.length === 0 && (
                <div className="text-gray-400 text-sm text-center py-6">无被排除时段</div>
              )}
              <div className="divide-y divide-gray-50 max-h-80 overflow-y-auto">
                {excluded.map((s, i) => (
                  <div key={i} className="px-4 py-2.5 text-sm">
                    <div className="flex items-center">
                      <span className="text-gray-400 mr-3">✗</span>
                      <span className="text-gray-500">{weekdayLabels[s.weekday]}</span>
                      {s.date && <span className="text-gray-400 ml-2">{s.date}</span>}
                      <span className="text-gray-400 ml-2">{timeSlotLabels[s.time_slot] || s.time_slot}</span>
                      {s.room && <span className="text-gray-300 ml-3">{s.room}</span>}
                    </div>
                    <div className="text-xs text-red-400 mt-1 ml-7">{s.reason}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 提交申请（F6）——先看结果再提交 */}
            <div className="bg-white rounded-xl border border-blue-200 p-5 mb-6">
              <h3 className="font-medium text-blue-800 mb-2">📋 确认提交调课申请</h3>
              <p className="text-sm text-gray-600 mb-4">
                {currentTeacher} · {selectedCourse.course_name} → 第{targetWeek}周（提交后由管理员审批）
              </p>
              {requestStatus ? (
                <div className="text-sm px-4 py-3 bg-green-50 border border-green-200 text-green-700 rounded-lg">
                  {requestStatus}
                </div>
              ) : (
                <button
                  onClick={handleSubmitRequest}
                  disabled={loading}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition-colors"
                >
                  {loading ? '提交中...' : '提交调课申请'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* 页面5：选课咨询 / 实验辅导（LLM 咨询） */}
        {(view === 'course_select' || view === 'tutor') && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              {view === 'course_select' ? '🎓 选课咨询' : '🔬 实验辅导'}
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              {view === 'course_select'
                ? '咨询选课资格、先修课程、学分要求等问题'
                : '咨询实验原理、数据处理、误差分析、报告规范等问题'}
            </p>

            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200">
              <div className="flex gap-2">
                <input
                  value={consultQ}
                  onChange={(e) => setConsultQ(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleConsult()}
                  placeholder={view === 'course_select'
                    ? '如：为什么我选不了大学物理实验课？'
                    : '如：扭摆法测转动惯量的误差来源？'}
                  className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  disabled={loading}
                />
                <button
                  onClick={handleConsult}
                  disabled={loading || !consultQ.trim()}
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
                >
                  {loading ? '思考中...' : '提问'}
                </button>
              </div>

              {consultMsg && (
                <div className="mt-4 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 prose prose-sm max-w-none">
                  <ReactMarkdown>{consultMsg}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
