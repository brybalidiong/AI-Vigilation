import {createApp,h} from 'vue';
import {createRouter,createMemoryHistory} from 'vue-router';
import '/src/assets/main.css';
const screen=new URLSearchParams(location.search).get('screen')||'login';
const role=screen.split('-')[0];
const user={name:'Alex Rivera',first_name:'Alex',last_name:'Rivera',full_name:'Alex Rivera',email:'alex@example.test',role,face_registered:false};
localStorage.setItem('user',JSON.stringify(user));localStorage.removeItem('access_token');localStorage.removeItem('refresh_token');
const courses=[{id:1,code:'IT321',name:'Software Engineering',instructor_name:'Morgan Lee',student_count:24,exam_count:3,set_count:2,announcements:'Welcome to Software Engineering. Review the assessment schedule and prepare your workspace.',sets:[{id:1,name:'BSIT 3A'}]},{id:2,code:'CS212',name:'Data Structures',instructor_name:'Jamie Chen',student_count:28,exam_count:2,set_count:2},{id:3,code:'IT315',name:'Database Systems',instructor_name:'Taylor Quinn',student_count:22,exam_count:2,set_count:1}];
const now=Date.now();const iso=n=>new Date(now+n*3600000).toISOString();
const exams=[{id:1,title:'Midterm Assessment',subject_id:1,subject_code:'IT321',subject_name:'Software Engineering',available_from:iso(-2),due_at:iso(24),created_at:iso(-48),time_limit_minutes:60,max_attempts:2,question_count:4,assigned_set_id:1,assigned_set_name:'BSIT 3A',is_finalized:true,is_done:false,attempts_used:0},{id:2,title:'Requirements Analysis Quiz',subject_id:1,subject_code:'IT321',subject_name:'Software Engineering',available_from:iso(48),due_at:iso(72),created_at:iso(-24),time_limit_minutes:30,max_attempts:1,question_count:10,is_finalized:true,is_done:false,assigned_set_id:2,assigned_set_name:'BSIT 3B'},{id:3,title:'Practice Assessment',subject_id:1,subject_code:'IT321',subject_name:'Software Engineering',available_from:iso(-48),due_at:iso(-24),created_at:iso(-72),time_limit_minutes:20,max_attempts:2,question_count:5,is_done:true,score:80,assigned_set_id:1,assigned_set_name:'BSIT 3A'}];
const questions=[{id:1,question_type:'multiple_choice',question_text:'Which activity defines what a software system should do?',choices:['Requirements analysis','Deployment','Maintenance','Code compilation'],correct_answer:'Requirements analysis',points:1},{id:2,question_type:'identification',question_text:'Identify the document that records the functional requirements of a system.',correct_answer:'Software Requirements Specification',points:1,case_sensitive:false},{id:3,question_type:'enumeration',question_text:'List three phases of the software development life cycle.',correct_answer:'Analysis\nDesign\nImplementation',points:3},{id:4,question_type:'essay',question_text:'Explain why validating requirements with stakeholders reduces project risk.',points:10}];
const students=[{id:1,full_name:'Sam Parker',first_name:'Sam',last_name:'Parker',email:'sam@example.test',is_enrolled:true,face_status:'pending'},{id:2,full_name:'Jordan Ellis',first_name:'Jordan',last_name:'Ellis',email:'jordan@example.test',is_enrolled:true,face_status:'approved',face_reupload_allowed:false},{id:3,full_name:'Casey Morgan',first_name:'Casey',last_name:'Morgan',email:'casey@example.test',is_enrolled:true,face_status:'none'}];
const sets=[{id:1,name:'BSIT 3A',student_count:24},{id:2,name:'BSIT 3B',student_count:22}];
const progress=students.map((s,i)=>({student_id:s.id,student_email:s.email,student_name:s.full_name,set_id:1,set_name:'BSIT 3A',exam_id:1,exam_title:exams[0].title,subject_id:1,is_done:i!==2,score:i===2?null:80+i*5,attempt_count:1,attempts_used:1,max_attempts:2,started_at:iso(-1),submitted_at:i===2?null:iso(-0.2),integrity_score:96-i*8,status:i===2?'in_progress':'completed',terminated:false}));
const state={subjects:courses,subjectsLoading:false,exams,examsLoading:false,currentDate:'Tuesday, September 29, 2026',currentTime:'10:30 AM',selectedSubjectId:screen.includes('course')||screen.includes('section')||screen.includes('progress')||screen.includes('upload')||screen.includes('question')?1:null,upcomingExamRows:exams,subjectSets:sets,examSets:exams,subjectStudents:students,examProgressRows:progress,subjectsLoaded:true,upcomingLoaded:true,examSetsLoaded:true,subjectSetsLoaded:true,examProgressLoaded:true,instructors:[{id:1,full_name:'Morgan Lee',email:'morgan@example.test'},{id:2,full_name:'Jamie Chen',email:'jamie@example.test'}],students};
let route=role==='instructor'?'/instructor/dashboard':role==='student'?'/student/dashboard':'/';
if(screen.includes('courses')||screen.includes('create'))route=`/${role}/courses`;
if(screen.includes('course')&&!screen.includes('courses'))route=`/${role}/courses/1`;
if(screen.includes('settings')||screen.includes('profile'))route=`/${role}/settings`;
if(role==='instructor'&&['sections','batch','progress','upload','question','stats','integrity','grading','evidence','snapshots'].some(k=>screen.includes(k)))route='/instructor/courses/1';
if(screen==='instructor-create')state.showCreateCoursePanel=true;
if(screen==='instructor-upload')state.showUploadExamPanel=true;
if(screen.includes('sections')||screen==='instructor-batch'){state.activeCourseTab='sets';state.selectedSubjectSetId='1';state.showBatchEnroll=screen.includes('batch');}
if(screen.includes('progress')){state.activeCourseTab='exam-progress';state.selectedProgressSetId=1;state.selectedProgressExamId=1;state.selectedProgressStudentEmail=students[0].email;state.progressView=screen.endsWith('exam')?'exam':'student';}
if(screen.includes('question')){state.managingExam={...exams[0],is_finalized:false};state.examQuestions=questions;state.examIsFinal=false;state.newQ={type:screen.split('-')[2]||'multiple_choice',text:'',choices:['','','',''],correctIdx:0,enumerationItems:['','',''],points:'',correctAnswer:'',caseSensitive:false};}
if(screen==='instructor-stats'){state.statsExam=exams[0];state.examStatsSets=sets.map(s=>({...s,total_students:s.student_count,completed_count:18,in_progress_count:3,not_started_count:3,average_score:82}));state.examStatsExaminees=progress;}
if(['instructor-integrity','instructor-grading','instructor-evidence','instructor-snapshots'].includes(screen)){state.integrityReportOpen=true;state.activeIrTab=screen.includes('grading')?'grading':screen.includes('snapshots')?'snapshots':screen.includes('evidence')?'evidence':'log';state.integrityReportData={exam_title:exams[0].title,student_email:students[0].email,attempt_number:1,submission:{score:80,is_done:true,terminated:false},report:{integrity_score:96,tab_switch_count:1,gaze_violation_count:1,gaze_no_face_count:0,evidence_count:0},events:[{id:1,event_type:'gaze',type:'gaze',created_at:iso(-0.7),message:'Look-away warning recorded',details:{direction:'left'}},{id:2,event_type:'tab_switch',type:'tab_switch',created_at:iso(-0.4),message:'Student returned to the exam'}],evidence:[],subjective_answers:[{answer_id:4,question_id:4,question_text:questions[3].question_text,question_type:'essay',answer_text:'Early validation helps the team confirm stakeholder needs, find conflicting requirements, and reduce rework.',student_answer:'Early validation helps the team confirm stakeholder needs, find conflicting requirements, and reduce rework.',points:10,max_points:10,manual_score:null,score:null,instructor_feedback:'',_grade_score:'',_grade_feedback:''}]};}
if(screen==='admin-instructors'||screen==='admin-register'){state.activeTab='instructors';state.showAddInstructor=screen.endsWith('register');}
if(screen==='admin-students'||screen==='admin-enroll'){state.activeTab='students';state.showAddStudent=screen.endsWith('enroll');}
if(screen==='login-admin-flip')state.showAdminLogin=true;
if(screen==='student-results'){state.resultsModal=exams[0];state.resultsData={mc_score:80,mc_correct:8,mc_total:10,integrity_score:96,started_at:iso(-1),submitted_at:iso(-0.2)};}
if(screen.startsWith('student-exam')||['student-warning','student-face-hold'].includes(screen)){state.takingExam=exams[0];state.examQuestions=questions;state.examTimeRemaining=2700;state.currentQuestionIndex=Math.max(0,['multiple_choice','identification','enumeration','essay'].indexOf(screen.split('-')[2]));if(screen==='student-warning')state.proctoringWarning={show:true,type:'gaze',title:'Look-away warning',message:'Please keep your attention on the exam screen.'};if(screen==='student-face-hold'){state.examFaceHold=true;state.faceAbsentSeconds=5;}}
if(screen==='student-permissions')state.showPermissionModal=true;
if(screen.startsWith('student-face-')&&screen!=='student-face-hold'){state.fvShow=true;state.fvStep=screen.slice('student-face-'.length);}
if(screen==='student-terminated'){state.examTerminated=true;state.terminateReason='gaze';state.gazeViolationCount=8;}
if(screen.endsWith('empty')){state.subjects=[];state.exams=[];state.upcomingExamRows=[];}
if(screen.endsWith('loading')){state.subjectsLoading=true;state.examsLoading=true;state.upcomingLoading=true;}
if(screen==='student-confirm'){state.confirmOpen=true;state.confirmTitle='Log out?';state.confirmMessage='Are you sure you want to log out of your account?';}
for(const row of progress){row.student_set_id=1;row.student_set_name='BSIT 3A';row.exam_set_id=1;}
if(state.integrityReportData?.subjective_answers)state.integrityReportData.subjective_answers[0].order=4;
if(state.examStatsSets)for(const row of state.examStatsSets){row.total=row.student_count;row.done=18;}
if(state.examStatsExaminees)for(const row of state.examStatsExaminees){row.name=row.student_name;row.email=row.student_email;row.status=row.is_done?'Done':'In Progress';row.tab_switches=1;row.gaze_violation_count=1;row.gaze_no_face_count=0;}
if(screen.includes('courses-list'))state.courseView='list';
if(screen.includes('courses-summary'))state.courseView='summary';
if(screen.includes('settings-pending'))state.faceStatus='pending';
if(screen.includes('settings-approved')){state.faceStatus='approved';state.faceRegistered=true;}
if(screen.endsWith('settings-edit'))state.isEditing=true;
state.form={...user,mobile_number:'+63 900 000 0000'};
window.__designState=state;
const views=import.meta.glob('/src/views/*.vue');
const viewName=screen==='instructor-login'?'InstructorLoginView':screen==='admin-login'?'AdminLoginView':screen.startsWith('login')?'LoginView':role==='instructor'?'InstructorDashboardView':role==='student'?'StudentDashboardView':'AdminDashboardView';
const view=(await views[`/src/views/${viewName}.vue`]()).default;
const router=createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:view},{path:'/:role/courses/:courseId',component:view},{path:'/:role/courses/:courseId/sets/:setId',component:view}]});
await router.push(route);await router.isReady();
createApp({render:()=>h(view)}).use(router).mount('#app');
document.title=screen+' | AI-Vigilation';
if(role==='instructor'&&screen.includes('question')){
  const style=document.createElement('style');style.textContent='.dashboard-container{display:none!important}.qe-overlay{position:relative!important;inset:auto!important;overflow:visible!important;height:auto!important}.qe-shell{height:auto!important;max-height:none!important}';document.head.appendChild(style);
}
if(screen.includes('upload')||screen.includes('settings')||screen.includes('create')){
  const style=document.createElement('style');style.textContent='.dashboard-container{height:auto!important;min-height:100vh!important;overflow:visible!important}.main-content{height:auto!important;max-height:none!important;overflow:visible!important}.sidebar{min-height:100vh!important}.sidebar-footer-nav{margin-top:auto}';document.head.appendChild(style);
}
window.__designReady=true;
if(new URLSearchParams(location.search).get('auto')==='1'){
  const plan=await (await fetch('./capture-plan.json')).json();
  const item=plan.find(x=>x.screen===screen);
  if(item){
    await document.fonts.ready;
    for(let i=0;i<100&&!window.figma?.captureForDesign;i++)await new Promise(r=>setTimeout(r,100));
    await new Promise(r=>setTimeout(r,600));
    const next=plan[plan.indexOf(item)+1];
    window.figma.captureForDesign({captureId:item.id,endpoint:`https://mcp.figma.com/mcp/capture/${item.id}/submit?bindVariables=true`,selector:'body'}).then(result=>console.info('Design captured',screen,result)).catch(error=>console.error('Design capture error',screen,error));
    if(next)setTimeout(()=>location.assign('./preview.html?screen='+encodeURIComponent(next.screen)+'&auto=1'),10000);
  }
}
