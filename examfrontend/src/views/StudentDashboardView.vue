<template>
  <div class="app-wrapper dashboard-role dashboard-role--student">

    <!-- â”€â”€â”€ ROOT-LEVEL TERMINATED SCREEN (survives after exam closes) â”€â”€â”€ -->
    <ProctoringOverlay 
      :terminated="examTerminated" 
      :switchCount="browserWarningCount"
      :terminateReason="terminateReason"
      :gazeViolationCount="gazeViolationCount"
      :gazeNoFaceCount="gazeNoFaceCount"
      :gazeViolationLimit="GAZE_VIOLATION_LIMIT"
      :gazeNoFaceLimit="GAZE_NO_FACE_LIMIT"
      :gadgetWarningCount="gadgetWarningCount"
      :gadgetWarningLimit="GADGET_WARNING_LIMIT"
      @dismiss="dismissTerminatedScreen" 
    />

    <div v-if="takingExam && browserWarning.show" class="proctor-overlay browser-leave-overlay" role="alertdialog" aria-modal="true" aria-labelledby="browser-warning-title">
      <div class="proctor-box alttab">
        <div class="proctor-icon" aria-hidden="true">!</div>
        <h2 id="browser-warning-title">{{ browserWarning.title }}</h2>
        <p>{{ browserWarning.message }}</p>
        <div class="proctor-counter">
          <span class="strike-count">{{ browserWarningCount }}</span>
          <span class="strike-label">/ {{ TAB_SWITCH_LIMIT }} warnings</span>
        </div>
        <button type="button" class="proctor-dismiss" :disabled="browserWarning.type === 'extended_monitor' && _extendedDisplayActive" @click="dismissBrowserWarning">{{ browserWarning.type === 'extended_monitor' && _extendedDisplayActive ? 'Disconnect the additional display to continue' : 'I Understand — Return to Exam' }}</button>
      </div>
    </div>

    <div class="dashboard-container">
      
      <!-- LEFT SIDEBAR -->
      <aside class="sidebar">
        <div class="sidebar-logo">
          <span class="sidebar-brand-mark" aria-hidden="true">AI</span>
          <span class="sidebar-brand-lockup">
            <span class="sidebar-brand-name">AI-Vigilation</span>
            <span class="sidebar-brand-context">Student workspace</span>
          </span>
        </div>
        <nav class="sidebar-nav">
          <a href="#" class="nav-item" :class="{ active: activeNav === 'dashboard' }" @click.prevent="goStudentDashboard">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect></svg>
            Dashboard
          </a>
          <a href="#" class="nav-item" :class="{ active: activeNav === 'courses' }" @click.prevent="goStudentCourses">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            Courses
          </a>
        </nav>
        <div class="sidebar-footer-nav">
          <div class="sidebar-user-info">
            <div class="sidebar-user-avatar">{{ studentFullName[0]?.toUpperCase() || 'S' }}</div>
            <div class="sidebar-user-text">
              <span class="sidebar-user-name">{{ studentFullName }}</span>
              <span class="sidebar-user-role">Student</span>
            </div>
          </div>
          <a href="#" class="nav-item" :class="{ active: activeNav === 'settings' }" @click.prevent="goSettings">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="8" r="4"></circle>
              <path d="M4 21a8 8 0 0 1 16 0"></path>
            </svg>
            Profile
          </a>
          <a href="#" class="nav-item logout-nav" @click.prevent="requestLogout">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            Log Out
          </a>
        </div>
      </aside>

      <!-- CENTER CONTENT -->
      <main class="main-content" :class="{ 'main-content--dashboard': activeNav === 'dashboard' }">
         <header class="main-header" v-show="!(activeNav === 'courses' && isCourseDetailRoute)">
          <div class="header-titles">
            <span class="dashboard-eyebrow">{{ currentDate }}</span>
            <h1>{{ pageTitle }}</h1>
            <p v-if="activeNav === 'settings'" class="header-sub">Your personal details and exam ID photo.</p>
            <p v-else class="header-sub">Welcome back, {{ studentFullName }}!</p>
          </div>
          <div class="header-actions">
            <div class="role-pill">Student</div>
          </div>
        </header>

        <template v-if="activeNav === 'dashboard'">
          <section class="dashboard-welcome">
            <div class="dashboard-welcome__copy">
              <span class="dashboard-welcome__eyebrow">Student overview</span>
              <h2>Stay ready for your next assessment.</h2>
              <p>Review upcoming schedules, open your courses, and start available exams from one place.</p>
            </div>
            <button type="button" class="dashboard-welcome__action" @click="goStudentCourses">
              Browse courses
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
            </button>
          </section>

        <div class="moodle-card dashboard-agenda">
          <div class="agenda-header">
            <div class="agenda-header__copy">
              <h2 class="moodle-section-title">Exam timeline</h2>
              <p class="agenda-header__subtitle">Your upcoming schedules and important dates.</p>
            </div>
            <button type="button" class="agenda-view-all" @click="goStudentCourses">
              View all
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
            </button>
          </div>

          <div class="moodle-filters agenda-filters">
            <div class="select-wrapper agenda-filter-select">
              <select v-model="timelineWindowDays" class="moodle-select">
                <option value="7">Next 7 days</option>
                <option value="14">Next 14 days</option>
                <option value="30">Next 30 days</option>
                <option value="90">Next 90 days</option>
                <option value="3650">All upcoming</option>
              </select>
            </div>
            <div class="agenda-search-wrap">
              <svg class="agenda-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>
              </svg>
              <input v-model.trim="timelineSearch" type="text" class="moodle-search agenda-search" placeholder="Search exams, subjects..." />
            </div>
            <span class="agenda-order-label">Newest added first</span>
          </div>

          <div class="moodle-timeline-list dashboard-timeline-scroll agenda-timeline">
            <template v-if="examsLoading">
              <SkeletonLoader type="row" v-for="i in 3" :key="i" />
            </template>
            <EmptyState 
              v-else-if="filteredDueExamTimeline.length === 0" 
              title="No upcoming exams" 
              description="You have no open or upcoming exams at the moment. Past due exams appear under Courses." 
              icon='<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>'
            />
            <template v-else>
              <ExamRow
                v-for="exam in filteredDueExamTimeline"
                :key="`${exam.subject_id}-${exam.id}`"
                :dateIso="examTimelineDisplayAt(exam)"
                :timeText="formatExamTimelineTime(exam)"
                :title="formatDisplayTitle(exam.title)"
                :subtitle="formatDisplayTitle(`${exam.subject_code} ${exam.subject_name}`)"
                :status="getExamStatus(exam)"
                :statusClass="statusClass(exam)"
              >
                <template #actions>
                  <button v-if="exam.is_done" type="button" class="moodle-btn-ghost" @click="openResultsModal(exam)">Results</button>
                  <button v-if="canRetakeExam(exam)" type="button" class="moodle-btn-ghost timeline-btn-primary" @click="openTakeExam(exam)">Retake exam</button>
                  <button v-if="!exam.is_done" type="button" class="moodle-btn-ghost timeline-btn-primary" @click="openTakeExam(exam)">Take Exam</button>
                </template>
              </ExamRow>
            </template>
          </div>
        </div>
        </template>

        <div v-else-if="activeNav === 'settings'" style="width: 100%;">
          <div class="workspace-area">
          <UserProfileSettings 
              :user="user" 
              :loading="profileLoading"
              :errorMsg="profileError"
              :successMsg="profileSuccess"
              :faceRegistered="faceRegistered"
              :facePhotoUrl="facePhotoUrl"
              :faceError="faceError"
              :faceStatus="faceStatus"
              :faceReuploadAllowed="faceReuploadAllowed"
              @save-profile="handleProfileUpdate"
              @dismiss-notice="profileError = ''; profileSuccess = ''"
            />
          </div>
        </div>

        <div v-if="activeNav === 'courses' && !isCourseDetailRoute">
           <div class="moodle-filters" style="display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-start; align-items: center; margin-bottom: 2rem;">
             <div class="select-wrapper">
               <select v-model="courseFilter" class="moodle-select">
                 <option value="all">All</option>
                 <option value="in_progress">In progress</option>
                 <option value="future">Future</option>
                 <option value="past">Past</option>
               </select>
             </div>
             <input v-model.trim="courseSearch" type="text" class="moodle-search" placeholder="Search" style="flex: 1;" />
             <div class="select-wrapper">
               <select v-model="courseSort" class="moodle-select">
                 <option value="name_asc">Sort by course name</option>
                 <option value="name_desc">Sort by course name (Z - A)</option>
               </select>
             </div>
             <div class="select-wrapper">
               <select v-model="courseView" class="moodle-select">
                 <option value="card">Card</option>
                 <option value="list">List</option>
                 <option value="summary">Summary</option>
               </select>
             </div>
           </div>
           <TransitionGroup name="list" tag="div" class="courses-grid">
             <template v-if="subjectsLoading">
               <SkeletonLoader type="card" v-for="i in 3" :key="`skel-${i}`" />
             </template>
             <EmptyState 
               v-else-if="displayedCourses.length === 0" 
               style="grid-column: 1 / -1;" 
               title="No courses found" 
               description="You have no courses matching this filter." 
               icon='<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line>'
             />
             <template v-else>
               <CourseCard
                 v-for="(subject, index) in displayedCourses"
                 :key="subject.id"
                 :folderClass="['folder-1','folder-2','folder-3','folder-4','folder-5'][index % 5]"
                 :code="subject.code"
                 :name="subject.name"
                 :meta="`${subject.instructor_name} · ${selectedCourseExamsCount(subject.id)} exam${selectedCourseExamsCount(subject.id) !== 1 ? 's' : ''}`"
                 :photo="subject.display_photo"
                 @click="openStudentCourse(subject.id)"
               />
             </template>
           </TransitionGroup>
        </div>

        <div class="course-workspace" v-if="activeNav === 'courses' && isCourseDetailRoute">
          <!-- Hero banner -->
          <div class="cw-hero">
            <div class="cw-hero__content">
              <nav class="cw-hero__nav">
                <button type="button" class="cw-back-btn" @click="backToStudentCourses">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                  Back
                </button>
              </nav>
              <div class="cw-title-row" style="color:#fff;">
                <span v-if="selectedCourse" class="cw-hero__code">{{ selectedCourse.code }}</span>
                <h1 class="cw-hero__title" style="color:#fff;">{{ selectedCourse?.name || selectedCourseLabel }}</h1>
              </div>
              <div class="cw-hero__stats">
                <span class="cw-stat-chip">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  <strong>{{ selectedCourseExams.length }}</strong> exam{{ selectedCourseExams.length !== 1 ? 's' : '' }}
                </span>
                <span v-if="selectedCourse?.instructor_name" class="cw-stat-chip">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  {{ selectedCourse.instructor_name }}
                </span>
              </div>
            </div>
          </div>

          <!-- Exams list -->
          <div class="course-tabs-card">
            <div class="course-tab-panel">
              <div class="moodle-timeline-list dashboard-timeline-scroll agenda-timeline">
                <template v-if="examsLoading">
                  <SkeletonLoader type="row" v-for="i in 3" :key="i" />
                </template>
                <EmptyState
                  v-else-if="selectedCourseExams.length === 0"
                  title="No exams found"
                  description="No uploaded exams in this course yet."
                  icon='<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline>'
                />
                <template v-else>
                  <ExamRow
                    v-for="exam in selectedCourseExams"
                    :key="`${exam.subject_id}-${exam.id}`"
                    :dateIso="examTimelineDisplayAt(exam)"
                    :timeText="formatExamTimelineTime(exam)"
                    :title="formatDisplayTitle(exam.title)"
                    :subtitle="formatDisplayTitle(`${exam.subject_code} ${exam.subject_name}`)"
                    :status="getExamStatus(exam)"
                    :statusClass="statusClass(exam)"
                  >
                    <template #actions>
                      <button v-if="exam.is_done" type="button" class="moodle-btn-ghost" @click="openResultsModal(exam)">Results</button>
                      <button v-if="canRetakeExam(exam)" type="button" class="moodle-btn-ghost timeline-btn-primary" @click="openTakeExam(exam)">Retake exam</button>
                      <button v-if="!exam.is_done" type="button" class="moodle-btn-ghost timeline-btn-primary" @click="openTakeExam(exam)">Take Exam</button>
                    </template>
                  </ExamRow>
                </template>
              </div>
            </div>
          </div>
        </div>
      </main>

    <!-- RIGHT PANEL REMOVED FOR MORE SPACE -->
    </div>

    <!-- FACE VERIFICATION MODAL -->
    <FaceVerificationModal
      :show="fvShow"
      :step="fvStep"
      :attemptsLeft="fvAttemptsLeft"
      :errorMessage="fvErrorMsg"
      @retry="_onFaceVerifyRetry"
      @cancel="_onFaceVerifyCancel"
    />

    <!-- CAMERA PERMISSION MODAL -->
    <div v-if="showPermissionModal" class="overlay-modal">
      <div class="modal-card perm-card">
        <div class="perm-header">
          <div class="perm-icon-ring">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="32" height="32">
              <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
          </div>
          <h2>System Pre-Check</h2>
          <p>This exam requires your camera, microphone, and entire-screen sharing. Screen sharing lets your instructor review the screen shown when you leave the exam tab.</p>
        </div>

        <div class="perm-preview-wrap">
          <video ref="permVideoEl" class="perm-video" autoplay muted playsinline></video>
          <div v-if="!mediaStreamActive" class="perm-video-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40" style="opacity:0.4">
              <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
            <span>Camera preview will appear here</span>
          </div>
          <div v-if="mediaStreamActive" class="perm-live-badge">
            <span class="perm-live-dot"></span> LIVE
          </div>
        </div>

        <p class="perm-caution">Caution: Sitting too far from the camera may cause "face not detected" violations during the exam.</p>
        <p class="perm-caution">Choose <strong>Entire Screen</strong> in the browser sharing prompt. Disconnect any additional monitor before continuing. The exam records a screen image only when you leave the exam window; other tab URLs are not available to the site.</p>
        <p v-if="mediaStreamActive" class="perm-face-status" :class="`perm-face-status--${precheckStatus}`" role="status">{{ precheckMessage }}</p>
        <p v-if="screenShareReady" class="perm-face-status perm-face-status--ready" role="status">Entire-screen sharing is active.</p>
        <p v-if="permissionError" class="perm-error">⚠️ {{ permissionError }}</p>

        <div class="perm-actions">
          <button class="ghost-btn" @click="cancelPermissionModal" :disabled="permissionLoading || screenShareLoading">Cancel</button>
          <button v-if="mediaStreamActive && precheckStatus === 'unavailable'" class="ghost-btn" @click="_startPrecheckFaceCheck">Retry face check</button>
          <button v-if="mediaStreamActive && !screenShareReady" class="ghost-btn" @click="requestScreenShare" :disabled="screenShareLoading">
            {{ screenShareLoading ? 'Requesting screen...' : 'Share entire screen' }}
          </button>
          
          <template v-if="mediaStreamActive">
             <button class="primary-btn perm-allow-btn" @click="proceedFromPermissionModal()" :disabled="!precheckFaceVisible || !screenShareReady || screenShareLoading">
               <span v-if="precheckStatus === 'checking'" class="perm-spinner"></span>
               {{ !screenShareReady && precheckFaceVisible ? 'Share screen to continue' : precheckFaceVisible ? 'Continue to Exam' : precheckStatus === 'too_far' ? 'Move closer to continue' : 'Checking face...' }}
             </button>
          </template>
          <template v-else>
             <button class="primary-btn perm-allow-btn" @click="requestMediaPermissions()" :disabled="permissionLoading">
               <span v-if="permissionLoading" class="perm-spinner"></span>
               {{ permissionLoading ? 'Requesting Access...' : 'Allow Camera &amp; Mic' }}
             </button>
          </template>
        </div>
      </div>
    </div>

    <!-- FLOATING CAMERA PiP (visible whenever stream is active) -->
    <div v-if="mediaStreamActive" class="cam-pip">
      <div class="cam-pip-inner" :style="{ boxShadow: pipBorderGlow, borderColor: pipBorderColor, transition: 'box-shadow 0.12s ease, border-color 0.12s ease' }">
        <video ref="examVideoEl" class="cam-pip-video" autoplay muted playsinline></video>

        <!-- Direction label overlay (replaces bounding box) -->
        <div v-if="takingExam && gazeDisplayDirection" class="cam-pip-direction-badge" :style="{ background: pipBorderColor }">
          {{ gazeDirectionIcon }} {{ gazeDirectionLabel }}
        </div>

        <div class="cam-pip-badge"><span class="perm-live-dot"></span> LIVE</div>

        <div v-if="takingExam" class="cam-pip-gaze">
          <span class="cam-pip-gaze-label">AI gaze<span v-if="gazeDetectionStatus"> · {{ gazeDetectionStatus }}</span></span>
          <span class="cam-pip-gadget-status" :class="{ 'cam-pip-gadget-unavailable': gadgetDetectionStatus === 'unavailable' }">Gadget scanner: {{ gadgetDetectionStatus }}</span>
          <span class="cam-pip-gaze-stats" :class="{ 'cam-pip-gaze-warn': gazeViolationCount > 0 || gazeNoFaceCount > 0 || gadgetWarningCount > 0 || gazeDisplayDirection }">
            away {{ gazeViolationCount }}/{{ GAZE_VIOLATION_LIMIT }} · face {{ gazeNoFaceCount }}/{{ GAZE_NO_FACE_LIMIT }} · gadget {{ gadgetWarningCount }}/{{ GADGET_WARNING_LIMIT }}
          </span>
        </div>
      </div>

      <!-- Live direction alert: sits BELOW the video box so it never covers the face -->
      <Transition name="dir-alert">
        <div v-if="takingExam && gazeDisplayDirection" class="cam-pip-dir-alert">
          <span class="cam-pip-dir-icon">{{ gazeDirectionIcon }}</span>
          <div class="cam-pip-dir-body">
            <span class="cam-pip-dir-label">{{ gazeDirectionLabel }}</span>
          </div>
        </div>
      </Transition>
    </div>

    <!-- EXAM MODAL (taking mode only) -->
    <div v-if="takingExam" class="fullscreen-modal exam-taking-screen no-capture">

      <div v-if="absenceAlert.show" class="absence-toast" role="alert" aria-live="assertive">
        <span class="absence-toast-icon" aria-hidden="true">!</span>
        <div class="absence-toast-text">
          <strong>Not visible on camera</strong>
          <span>{{ absenceAlert.message }}</span>
        </div>
      </div>

      <div v-if="examFaceHold" class="face-hold-overlay" role="alertdialog" aria-modal="true" aria-labelledby="face-hold-title">
        <div class="face-hold-panel">
          <h2 id="face-hold-title">Return to camera view</h2>
          <p>Your face has not been visible for {{ Math.ceil(faceAbsentSeconds) }} seconds. The exam is paused until proctoring can see you again.</p>
        </div>
      </div>

      <!-- Detector and restricted-action warnings. Browser departure warnings live above the exam modal. -->
      <div v-if="proctoringWarning.show" class="proctor-overlay">
        <div class="proctor-box" :class="proctoringWarning.type">
          <div class="proctor-icon">
            <svg v-if="proctoringWarning.type === 'splitscreen'" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/>
            </svg>
            <svg v-else-if="proctoringWarning.type === 'cheat'" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <svg v-else-if="proctoringWarning.type === 'gaze'" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            <svg v-else width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <h2>{{ proctoringWarning.title }}</h2>
          <p>{{ proctoringWarning.message }}</p>
          <div v-if="proctoringWarning.type === 'alttab' || proctoringWarning.type === 'gadget'" class="proctor-counter">
            <span class="strike-count">{{ proctoringWarning.type === 'gadget' ? gadgetWarningCount : browserWarningCount }}</span>
            <span class="strike-label">/ {{ proctoringWarning.type === 'gadget' ? GADGET_WARNING_LIMIT : 5 }} warnings</span>
          </div>
          <button
            class="proctor-dismiss"
            :class="{ 'proctor-dismiss-blocked': proctoringWarning.type === 'splitscreen' && isSplitScreen }"
            @click="dismissProctoringWarning"
            id="proctor-dismiss-btn"
          >
            <template v-if="proctoringWarning.type === 'splitscreen' && isSplitScreen">
              ⛔ Maximize your window to continue
            </template>
            <template v-else>
              I Understand — Return to Exam
            </template>
          </button>
        </div>
      </div>

      <div style="width: 100%; max-width: 100%; padding: 3rem 5%; padding-bottom: 8rem;">
        
        <!-- Header / Course Name -->
        <h1 style="font-size: 1.9rem; font-weight: 700; color: #37302a; margin-bottom: 2rem; border-bottom: 1px solid #d4d4d4; padding-bottom: 1rem;">
          {{ takingExam.subject_code ? takingExam.subject_code + '_' : '' }}{{ takingExam.title?.toUpperCase().replace(/\s+/g, '_') }}
        </h1>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <!-- Alt-tab strike indicator -->
            <div class="strike-indicator" :class="browserWarningCount >= 4 ? 'danger' : browserWarningCount >= 2 ? 'warning' : ''">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              Warnings: {{ browserWarningCount }}/5
            </div>
          </div>
        </div>

        <div v-if="takingLoading" style="margin-top:2rem;">
          <SkeletonLoader type="text" width="60%" height="2rem" />
          <br /><br />
          <SkeletonLoader type="card" height="300px" />
        </div>
        <EmptyState 
          v-else-if="examQuestions.length === 0" 
          style="margin-top:2rem;" 
          title="No questions" 
          description="No questions have been added to this exam yet." 
        />
        <div v-else>

          <!-- Single Question Display -->
          <div style="display: grid; grid-template-columns: 180px 1fr; gap: 1.5rem; margin-bottom: 2rem;">

            <!-- Left Info Block -->
            <div class="exam-question-info" style="padding: 1.5rem 1rem; border-radius: 8px; border: 1px solid #cbd2da; height: fit-content;">
              <h4 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; color: #334155; font-weight: 600;">Question <span style="font-size: 1.25rem;">{{ currentQuestionIndex + 1 }}</span> of {{ examQuestions.length }}</h4>
              <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 1.5rem;">
                <span v-if="studentAnswers[currentQuestion.id]">Answered</span>
                <span v-else>Not yet answered</span>
              </div>
              <button style="background: none; border: none; padding: 0; color: #3b82f6; cursor: pointer; display: flex; align-items: center; gap: 0.35rem; font-size: 0.85rem;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
                Flag question
              </button>
            </div>

            <!-- Right Question Block -->
            <div class="exam-question-panel" style="padding: 1.5rem; border-radius: 8px;">
              <p style="margin: 0 0 1.5rem 0; font-size: 1.05rem; color: #1e1b4b; line-height: 1.6;">{{ currentQuestion.question_text }}</p>

              <!-- Multiple Choice -->
              <div v-if="currentQuestion.question_type === 'multiple_choice'" style="display: flex; flex-direction: column; gap: 0.75rem;">
                <label v-for="(choice, cIdx) in currentQuestion.choices" :key="cIdx" style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; color: #312e81;">
                  <div style="display: flex; align-items: center; justify-content: center; width: 16px; height: 16px; border-radius: 50%; border: 1px solid #64748b; background: #fff; position:relative;">
                    <input type="radio" :name="'q_' + currentQuestion.id" :value="choice" v-model="studentAnswers[currentQuestion.id]" style="opacity: 0; position: absolute; width:100%; height:100%; cursor: pointer;" />
                    <div v-if="studentAnswers[currentQuestion.id] === choice" style="width: 8px; height: 8px; background: #1D3461; border-radius: 50%;"></div>
                  </div>
                  <span style="font-weight: 500; min-width: 1.2rem;">{{ String.fromCharCode(97 + cIdx) }}.</span>
                  <span>{{ choice }}</span>
                </label>
                <div style="margin-top: 0.5rem; margin-left: 2rem;">
                  <button v-if="studentAnswers[currentQuestion.id]" @click="studentAnswers[currentQuestion.id] = null" style="background: none; border: none; color: #4338ca; font-size: 0.9rem; cursor: pointer; padding:0;">Clear my choice</button>
                </div>
              </div>

              <!-- Identification: short answer -->
              <div v-else-if="currentQuestion.question_type === 'identification'">
                <p style="font-size: 0.82rem; color: #9d174d; margin-bottom: 0.5rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                  ✏️ Write your answer below:
                  <span v-if="currentQuestion.case_sensitive"
                    style="display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.72rem; font-weight: 600; color: #9d174d; background: #fff0f6; border: 1px solid #f9a8d4; border-radius: 20px; padding: 1px 8px; letter-spacing: 0.2px;">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    Case sensitive
                  </span>
                </p>
                <textarea v-model="studentAnswers[currentQuestion.id]" placeholder="Type your answer here..." style="width: 100%; min-height: 80px; padding: 1rem; border: 1px solid #fbcfe8; border-radius: 6px; font-family: inherit; resize: vertical; outline: none;"></textarea>
              </div>

              <!-- Enumeration: numbered list -->
              <div v-else-if="currentQuestion.question_type === 'enumeration'">
                <p style="font-size: 0.82rem; color: #15803d; margin-bottom: 0.75rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                  📋 List your answers (one per line or comma-separated):
                  <span v-if="currentQuestion.case_sensitive"
                    style="display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.72rem; font-weight: 600; color: #15803d; background: #f0fdf4; border: 1px solid #86efac; border-radius: 20px; padding: 1px 8px; letter-spacing: 0.2px;">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    Case sensitive
                  </span>
                </p>
                <textarea v-model="studentAnswers[currentQuestion.id]" placeholder="Apple&#10;Banana&#10;Orange&#10;(numbered also works: 1. Apple, 2. Banana)" style="width: 100%; min-height: 140px; padding: 1rem; border: 1px solid #86efac; border-radius: 6px; font-family: inherit; resize: vertical; outline: none;"></textarea>
              </div>

              <!-- Essay: long-form answer -->
              <div v-else-if="currentQuestion.question_type === 'essay'">
                <p style="font-size: 0.82rem; color: #92400e; margin-bottom: 0.5rem; font-weight: 600;">📝 Write your essay answer below:</p>
                <textarea v-model="studentAnswers[currentQuestion.id]" placeholder="Compose your answer here. Be thorough and support your points..." style="width: 100%; min-height: 220px; padding: 1rem; border: 1px solid #fde68a; border-radius: 6px; font-family: inherit; resize: vertical; outline: none; line-height: 1.65;"></textarea>
              </div>

              <!-- Fallback -->
              <div v-else>
                <textarea v-model="studentAnswers[currentQuestion.id]" placeholder="Type your answer here..." style="width: 100%; min-height: 120px; padding: 1rem; border: 1px solid #cbd5e1; border-radius: 4px; font-family: inherit; resize: vertical;"></textarea>
              </div>

            </div>
          </div>

          <!-- Prev / Next / Finish -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0;">
            <button type="button"
              style="background: #cbd5e1; color: #334155; padding: 0.6rem 1.2rem; border-radius: 6px; border: none; font-weight: 600; cursor: pointer;"
              :style="{ visibility: currentQuestionIndex > 0 ? 'visible' : 'hidden' }"
              @click.prevent="currentQuestionIndex--"
            >&larr; Previous</button>

            <div style="display: flex; align-items: center; gap: 1rem;">
              <div style="background: #fdf2f8; border: 1px solid #fbcfe8; color: #9d174d; padding: 0.5rem 1rem; border-radius: 4px; font-weight: 600;">
                Time left <span style="font-family: monospace;">{{ formattedTimeRemaining }}</span>
              </div>
              
              <button type="button" v-if="currentQuestionIndex < examQuestions.length - 1"
                style="background: #1D3461; color: white; padding: 0.6rem 1.5rem; border-radius: 6px; border: none; font-weight: 600; cursor: pointer;"
                @click.prevent="currentQuestionIndex++"
              >Next &rarr;</button>
  
              <button v-else
                style="background: #115e59; color: white; padding: 0.6rem 1.5rem; border-radius: 6px; border: none; font-weight: 600; cursor: pointer; font-size: 1rem;"
                @click="submitExam" :disabled="submitting"
              >{{ submitting ? 'Submitting...' : 'Finish attempt...' }}</button>
            </div>
          </div>
          <span class="muted" v-if="submitError" style="color: red; display:block; text-align:right; margin-top: 0.5rem;">{{ submitError }}</span>

          <!-- Quiz Navigation Grid -->
          <div style="margin-top: 3rem;">
            <h3 style="font-size: 1.1rem; margin-bottom: 1rem; color: #1e293b; font-weight: 700;">Quiz navigation</h3>
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem;">
              <div style="width: 38px; height: 38px; border-radius: 50%; overflow: hidden; background: #e2e8f0;">
                <img :src="`https://ui-avatars.com/api/?name=${studentFirstName}&background=c7d2fe&color=3730a3`" alt="Avatar" style="width: 100%; height: 100%; object-fit: cover;" />
              </div>
              <span style="font-weight: 600; color: #475569; font-size: 0.95rem;">{{ studentFirstName }}</span>
            </div>

            <div style="display: flex; flex-wrap: wrap; gap: 0.35rem; max-width: 500px;">
              <button
                v-for="(q, idx) in examQuestions"
                :key="'nav_'+q.id"
                @click="currentQuestionIndex = idx"
                style="width: 32px; height: 42px; border-radius: 4px; display: flex; flex-direction: column; overflow: hidden; cursor: pointer; padding: 0; border: none;"
                :style="{ border: idx === currentQuestionIndex ? '2px solid #1D3461' : '1px solid #cbd5e1', background: 'transparent' }"
              >
                <div style="flex: 1; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 600; color: #334155;">{{ idx + 1 }}</div>
                <div style="height: 18px; border-top: 1px solid #cbd5e1; background: #f1f5f9;">
                  <div v-if="studentAnswers[q.id]" style="height: 100%; background: #64748b;"></div>
                </div>
              </button>
            </div>

            <!-- Finish button at bottom -->
            <div style="margin-top: 2rem;">
              <button style="background: #115e59; color: white; padding: 0.6rem 1.5rem; border-radius: 6px; border: none; font-weight: 600; cursor: pointer; font-size: 1rem;" @click="submitExam" :disabled="submitting">
                {{ submitting ? 'Submitting...' : 'Finish attempt...' }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>


    <!-- RESULTS MODAL -->
    <div v-if="resultsModal" class="results-overlay">
      <div class="results-card">

        <!-- Header -->
        <div class="results-header">
          <div class="results-header-left">
            <div class="results-icon-wrap">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                <path d="M9 12l2 2 4-4"/>
              </svg>
            </div>
            <div>
              <p class="results-breadcrumb">{{ resultsModal.subject_code }} · {{ resultsModal.subject_name }}</p>
              <h2 class="results-title">{{ resultsModal.title }}</h2>
            </div>
          </div>
          <button class="results-close-btn" @click="closeResultsModal">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <!-- Score hero -->
        <div class="results-score-hero">
          <div class="results-score-ring">
            <svg viewBox="0 0 120 120" class="score-ring-svg">
              <circle cx="60" cy="60" r="50" fill="none" stroke="#e8e8e8" stroke-width="10"/>
              <circle cx="60" cy="60" r="50" fill="none"
                :stroke="(resultsData?.mc_score || 0) >= 75 ? '#00a699' : (resultsData?.mc_score || 0) >= 50 ? '#f59e0b' : '#e53e3e'"
                stroke-width="10"
                stroke-linecap="round"
                stroke-dasharray="314"
                :stroke-dashoffset="314 - (314 * Math.min((resultsData?.mc_score || 0), 100) / 100)"
                transform="rotate(-90 60 60)"
                style="transition: stroke-dashoffset 1s ease;"
              />
            </svg>
            <div class="score-ring-label">
              <span class="score-pct" v-if="resultsLoading && resultsData?.mc_total == null">…</span>
              <span class="score-pct" v-else>{{ resultsData?.mc_total != null ? (resultsData?.mc_score || 0).toFixed(0) : '—' }}</span>
              <span class="score-pct-sign" v-if="resultsData?.mc_total != null">%</span>
            </div>
          </div>
          <div class="results-score-info">
            <div class="score-fraction" v-if="resultsLoading && resultsData?.mc_total == null">
              <span class="score-pending">Loading score…</span>
            </div>
            <div class="score-fraction" v-else-if="resultsData?.mc_total != null">
              <span class="score-num">{{ (resultsData?.mc_correct || 0).toFixed(0) }}</span>
              <span class="score-denom"> / {{ (resultsData?.mc_total || 0).toFixed(0) }} correct</span>
            </div>
            <div class="score-fraction" v-else>
              <span class="score-pending">Pending grading</span>
            </div>
            <span class="score-badge"
              :class="(resultsData?.mc_score || 0) >= 75 ? 'badge-pass' : (resultsData?.mc_score || 0) >= 50 ? 'badge-average' : 'badge-fail'"
              v-if="resultsData?.mc_total != null">
              {{ (resultsData?.mc_score || 0) >= 75 ? 'Passed' : (resultsData?.mc_score || 0) >= 50 ? 'Average' : 'Failed' }}
            </span>
          </div>
        </div>

        <!-- Details grid -->
        <div class="results-details-grid">
          <div class="results-detail-item">
            <span class="detail-label">Status</span>
            <span class="detail-value detail-done">&#10003; Completed</span>
          </div>
          <div class="results-detail-item">
            <span class="detail-label">Started</span>
            <span class="detail-value">{{ formatFullDate(resultsData?.started_at || resultsModal.created_at) }}</span>
          </div>
          <div class="results-detail-item">
            <span class="detail-label">Submitted</span>
            <span class="detail-value">{{ formatFullDate(resultsData?.submitted_at || new Date()) }}</span>
          </div>
          <div class="results-detail-item">
            <span class="detail-label">Duration</span>
            <span class="detail-value">{{ formatDuration(resultsData?.started_at || resultsModal.created_at, resultsData?.submitted_at) }}</span>
          </div>
          <div class="results-detail-item">
            <span class="detail-label">Integrity Level</span>
            <span class="detail-value" v-if="resultsData?.integrity_score != null">
              {{ (resultsData.integrity_score).toFixed(0) }}%
              <span class="score-badge" style="font-size: 0.7em; margin-left: 8px; padding: 2px 6px;"
                :class="resultsData.integrity_score >= 80 ? 'badge-pass' : resultsData.integrity_score >= 50 ? 'badge-average' : 'badge-fail'">
                {{ resultsData.integrity_score >= 80 ? 'Excellent' : resultsData.integrity_score >= 50 ? 'Warning' : 'Critical' }}
              </span>
            </span>
            <span class="detail-value" v-else>Processing...</span>
          </div>
          <div class="results-detail-item">
            <span class="detail-label">Exam window</span>
            <span class="detail-value">{{ formatFullDate(resultsModal.available_from) }} – {{ formatFullDate(resultsModal.due_at) }}</span>
          </div>
          <div class="results-detail-item">
            <span class="detail-label">Attempts used</span>
            <span class="detail-value">{{ resultsModal.attempt_count || 1 }} of {{ resultsModal.max_attempts || 1 }}</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="results-footer">
          <p class="results-note">Review of answers is not permitted after submission.</p>
          <button v-if="canRetakeExam(resultsModal)" type="button" class="results-back-btn" @click="startRetakeFromResults">Retake exam</button>
          <button class="results-back-btn" @click="closeResultsModal">← Back</button>
        </div>

      </div>
    </div>

    <!-- Keep Original Modal -->
    <ConfirmModal
      v-model="confirmOpen"
      :title="confirmTitle"
      :message="confirmMessage"
      :variant="confirmVariant"
      :confirm-text="confirmConfirmText"
      :cancel-text="confirmCancelText"
      @confirm="onConfirmDialog"
      @cancel="clearPendingConfirm"
    />
    
    <NoticeModal :model-value="Boolean(toastMessage)" type="warning" title="Exam notice" :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import axios from "axios";
import { signOut } from "firebase/auth";
import { auth } from "@/firebase";
import { useRoute, useRouter } from "vue-router";
import ConfirmModal from "@/components/ConfirmModal.vue";
import NoticeModal from "@/components/NoticeModal.vue";
import ExamRow from "@/components/ExamRow.vue";
import CourseCard from "@/components/CourseCard.vue";
import ProctoringOverlay from "@/components/ProctoringOverlay.vue";
import FaceVerificationModal from "@/components/FaceVerificationModal.vue";
import SettingsPanel from "@/components/SettingsPanel.vue";
import SkeletonLoader from "@/components/SkeletonLoader.vue";
import EmptyState from "@/components/EmptyState.vue";

import UserProfileSettings from "@/components/UserProfileSettings.vue";
import { nextPrecheckFaceState } from "@/utils/precheckFace.js";
import { attachExamWindowMonitor } from "@/utils/examWindowMonitor.js";
import { hasExtendedDisplay, watchExtendedDisplays } from "@/utils/examDisplayMonitor.js";
import { captureSharedDisplayImage } from "@/utils/examScreenEvidence.js";
import {
  canRetakeExam,
  compareExamsNewestFirst,
  examTimelineDisplayAt,
  formatExamTimelineTime,
  studentExamOnDashboard,
} from "@/utils/examTimeline.js";

const router = useRouter();
const route = useRoute();

const confirmOpen = ref(false);
const confirmTitle = ref("");
const confirmMessage = ref("");
const confirmVariant = ref("neutral");
const confirmConfirmText = ref("Log out");
const confirmCancelText = ref("Cancel");
let pendingConfirm = null;

const toastMessage = ref("");

function showToastMessage(msg) {
  toastMessage.value = msg;
}

function openConfirm(opts) {
  confirmTitle.value = opts.title;
  confirmMessage.value = opts.message;
  confirmVariant.value = opts.variant ?? "neutral";
  confirmConfirmText.value = opts.confirmText ?? "Confirm";
  confirmCancelText.value = opts.cancelText ?? "Cancel";
  pendingConfirm = opts.onConfirm ?? null;
  confirmOpen.value = true;
}

function clearPendingConfirm() {
  pendingConfirm = null;
}

async function onConfirmDialog() {
  const fn = pendingConfirm;
  pendingConfirm = null;
  if (typeof fn === "function") {
    await fn();
  }
}

function requestLogout() {
  openConfirm({
    title: "Log out?",
    message: "You will be signed out of this device. Continue?",
    confirmText: "Log out",
    variant: "neutral",
    onConfirm: performLogout,
  });
}
const userStr = ref(localStorage.getItem("user") || "{}");
const user = computed(() => {
  try {
    return JSON.parse(userStr.value);
  } catch {
    return {};
  }
});

const studentFullName = computed(() => {
  const fullName = String(user.value?.name || '').trim();
  if (fullName) return fullName;
  const email = String(user.value?.email || '').trim();
  if (email.includes('@')) return email.split('@')[0];
  return 'Student';
});
// Keep alias for any other usages
const studentFirstName = studentFullName;

const profileLoading = ref(false);
const profileError = ref("");
const profileSuccess = ref("");
// Face ID registration state (populated from profile API response)
const faceRegistered      = ref(Boolean(user.value?.face_registered || false));
const facePhotoUrl        = ref(user.value?.face_photo_url || '');
const faceError           = ref('');
const faceStatus          = ref(user.value?.face_status || 'none');
const faceReuploadAllowed = ref(Boolean(user.value?.face_reupload_allowed || false));

async function handleProfileUpdate(formData) {
  profileLoading.value = true;
  profileError.value = "";
  profileSuccess.value = "";
  faceError.value = "";
  
  try {
    const response = await api.post("/api/auth/me/update/", formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 90000,  // 90s — DeepFace needs ~20-40s to load ArcFace on first use
    });
    
    // The backend returns { user: { ... }, face_encoding_error? }
    onSettingsUpdated(response.data.user);

    // Update face registration status
    if (response.data.user?.face_registered !== undefined) {
      faceRegistered.value = Boolean(response.data.user.face_registered);
    }
    facePhotoUrl.value = response.data.user?.face_photo_url || '';
    if (response.data.user?.face_status !== undefined) {
      faceStatus.value = response.data.user.face_status;
    }
    if (response.data.user?.face_reupload_allowed !== undefined) {
      faceReuploadAllowed.value = Boolean(response.data.user.face_reupload_allowed);
    }
    if (response.data.face_encoding_error) {
      faceError.value = response.data.face_encoding_error;
      profileSuccess.value = "Your profile was saved, but the face photo could not be accepted.";
    } else if (formData.has('face_photo')) {
      profileSuccess.value = "Your student ID was verified automatically. The ID portrait will be checked against your webcam before exams.";
    } else {
      profileSuccess.value = "Your profile has been updated.";
    }
    
  } catch (err) {
    profileError.value = err?.response?.data?.error || "Failed to update profile.";
  } finally {
    profileLoading.value = false;
  }
}

function onSettingsUpdated(updatedUser) {
  if (updatedUser) {
    localStorage.setItem("user", JSON.stringify(updatedUser));
    userStr.value = JSON.stringify(updatedUser);
  }
}

const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const subjects = ref([]);
const subjectsLoading = ref(true);
const subjectsError = ref("");
const exams = ref([]);
const examsLoading = ref(true);
const examsError = ref("");
const selectedSubjectId = ref(null);

const currentQuestionIndex = ref(0);
const currentQuestion = computed(() => examQuestions.value[currentQuestionIndex.value] || {});

const takingExam = ref(null);
const takingLoading = ref(false);
const submitting = ref(false);
const examQuestions = ref([]);
const studentAnswers = ref({});
const examResult = ref(null);
const submitError = ref("");
const activeExamRestrictions = ref({
  gaze_above: true,
  gaze_below: true,
  gaze_left: true,
  gaze_right: true,
  gadgets: true,
});

// â”€â”€â”€ Proctoring state â”€â”€â”€
const TAB_SWITCH_LIMIT = 5;
const GAZE_VIOLATION_LIMIT = 8;
const GAZE_NO_FACE_LIMIT = 5;
const GADGET_WARNING_LIMIT = 3;
const SPLIT_SCREEN_THRESHOLD = 0.98; // flag if window is not completely maximized
const browserWarningCount = ref(0);
const tabSwitchCount = ref(0);
const gazeViolationCount = ref(0);
const gazeNoFaceCount = ref(0);
const gadgetWarningCount = ref(0);
const gadgetDetectionStatus = ref('starting');
const gazeDetectionStatus = ref('');
const terminateReason = ref('tab');
const proctoringWarning = ref({ show: false, type: '', title: '', message: '' });
const browserWarning = ref({ show: false, title: '', message: '' });

// ── Notification sound ───────────────────────────────────────────────────────
function playWarningSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    osc.type = 'square';
    osc.frequency.setValueAtTime(400, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(600, ctx.currentTime + 0.1);
    
    gain.gain.setValueAtTime(0.05, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
    
    osc.start();
    osc.stop(ctx.currentTime + 0.2);
  } catch (e) {
    // Ignore audio errors
  }
}

watch(() => proctoringWarning.value.show, (newVal) => {
  if (newVal) {
    playWarningSound();
  }
});

const examTerminated = ref(false);
const examTimeRemaining = ref(null);
let _examTimer = null;

const formattedTimeRemaining = computed(() => {
  if (examTimeRemaining.value === null) return "Unlimited";
  const m = Math.floor(examTimeRemaining.value / 60).toString().padStart(2, '0');
  const s = (examTimeRemaining.value % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
});
// Listener refs
let _stopExamWindowMonitor = null;
let _resizeHandler = null;
let _keydownHandler = null;
let _keyupHandler = null;
let _beforeUnloadHandler = null;
let _copyHandler = null;
let _cutHandler = null;
let _contextHandler = null;
let _screenShareStream = null;
let _screenShareVideo = null;
const _lastShortcutLoggedAt = new Map();
const screenShareReady = ref(false);
const screenShareLoading = ref(false);
// State flags
let _isAway = false; // true while student is away â€” prevents double-counting
let _splitScreenActive = false;
let _browserTerminationPending = false;
let _leaveCaptureJob = null;
let _screenDetails = null;
let _stopExtendedDisplayMonitor = null;
let _extendedDisplayActive = false;
let _screenshotShortcutAt = 0;
const SCREEN_SWITCH_CAPTURE_DELAY_MS = 650;
const SCREENSHOT_FOCUS_GRACE_MS = 2500;
const PROCTORING_CAPTURE_INTERVAL_MS = 60000;
const GAZE_CHECK_INTERVAL_MS = 1000;       // no-face + HTTP fallback logging when WS is down
const GAZE_HTTP_FALLBACK_INTERVAL_MS = 1000;
const GAZE_WS_INTERVAL_MS = 0;            // sample a fresh frame on the next event-loop turn
const GAZE_WS_BUSY_RETRY_MS = 100;       // give the shared inference worker time to free up
const GAZE_FRAME_WIDTH = 640;              // preserve iris detail for gaze landmarks
const GAZE_FIRST_CHECK_MS = 50;            // fire first check immediately
const GAZE_CONFIDENCE_MIN = 0.34;          // match backend fallback when response thresholds are absent
const GAZE_ABOVE_CONFIDENCE_MIN = 0.22;    // match backend fallback when response thresholds are absent
const GAZE_LEFT_CONFIDENCE_MIN = 0.28;
const GAZE_RIGHT_CONFIDENCE_MIN = 0.30;
const GAZE_BELOW_CONFIDENCE_MIN = 0.25;
const GAZE_NO_FACE_HOLD_SECONDS = 10;
const GAZE_WARNING_COOLDOWN_MS = 5000;
const absenceAlert = ref({ show: false, message: 'Return to your webcam view so proctoring can see your face.' });
const examFaceHold = ref(false);
const faceAbsentSeconds = ref(0);
let _proctoringCaptureTimer = null;
let _gadgetDetectionTimer = null;
let _gadgetDetectionInFlight = false;
let _gadgetUnavailableNotified = false;
let _gadgetFailureCount = 0;
let _gadgetLoopActive = false;
let _gadgetLoopGeneration = 0;
let _gadgetCaptureCanvas = null;
const GADGET_FRAME_WIDTH = 640;
const GADGET_IDLE_POLL_MS = 150;
const GADGET_ACTIVE_POLL_MS = 0;
const GADGET_VISIBLE_POLL_MS = 100;
const GADGET_ERROR_POLL_MS = 500;
let _gazeCheckTimer = null;
let _lastGazeWarningAt = 0;
let _gazeCheckInFlight = false;
/** @type {{ kind: string, label: string } | null} */
let _gazePending = null;
const gazePendingActive = ref(false);
let _faceHoldSnapshotted = false;

async function _logProctoringEvent(eventType, { message = '', source = '', metadata = {}, severity = '' } = {}) {
  if (!takingExam.value || examTerminated.value) return null;
  try {
    const payload = {
      events: [{
        event_type: eventType,
        message,
        source,
        metadata,
        ...(severity ? { severity } : {}),
      }],
    };
    const { data } = await api.post(
      `/api/student/exams/${takingExam.value.id}/proctoring/events/`,
      payload,
    );
    return data?.events?.[0]?.id ?? null;
  } catch (err) {
    console.warn('Proctoring event log failed:', err);
    return null;
  }
}

/** Log a proctoring strike and capture webcam evidence immediately (linked to the event). */
async function _recordProctoringStrike(eventType, { message = '', source = '', metadata = {}, severity = '', caption = '' } = {}) {
  const examId = takingExam.value?.id;
  const eventId = await _logProctoringEvent(eventType, { message, source, metadata, severity });
  await _captureProctoringSnapshot(
    caption || message || `Proctoring: ${eventType}`,
    { eventId, examId },
  );
  return eventId;
}

function _notifyExamineeAbsent() {
  if (!absenceAlert.value.show && takingExam.value && !examTerminated.value) {
    void _logProctoringEvent('warning_shown', {
      message: 'Face-not-visible notice displayed during the exam',
      source: 'face_absence_notice',
      metadata: { warning_type: 'face_not_visible' },
      severity: 'info',
    });
  }
  absenceAlert.value = {
    show: true,
    message: 'Return to your webcam view so proctoring can see your face.',
  };
}

function _clearAbsenceAlert() {
  absenceAlert.value.show = false;
}

function _isLeftRightLabel(label) {
  const l = String(label || '').toLowerCase();
  return (l.includes('left') && !l.includes('right')) || (l.includes('right') && !l.includes('left'));
}

function _gazeConfidenceMet(label, confidence, thresholds = {}) {
  const general = thresholds.general ?? GAZE_CONFIDENCE_MIN;
  const above = thresholds.above ?? GAZE_ABOVE_CONFIDENCE_MIN;
  const left = thresholds.left ?? thresholds.leftRight ?? GAZE_LEFT_CONFIDENCE_MIN;
  const right = thresholds.right ?? thresholds.leftRight ?? GAZE_RIGHT_CONFIDENCE_MIN;
  const below = thresholds.below ?? GAZE_BELOW_CONFIDENCE_MIN;
  if (!label) return confidence >= general;
  const l = String(label).toLowerCase();
  if (l.includes('above')) return confidence >= above;
  if (l.includes('below')) return confidence >= below;
  if (l.includes('left')) return confidence >= left;
  if (l.includes('right')) return confidence >= right;
  return confidence >= general;
}

/** Convert a raw backend gaze label into a formal, user-facing phrase. */
function _formalGazeLabel(label) {
  const l = (label || '').toLowerCase();
  if (l === 'no_face' || l.includes('no_face'))     return 'Face Not Visible';
  if (l.includes('multiple'))                       return 'Multiple Faces Detected';
  if (l.includes('left') && !l.includes('right'))   return 'Looking Left';
  if (l.includes('right') && !l.includes('left'))   return 'Looking Right';
  if (l.includes('above'))                          return 'Looking Up';
  if (l.includes('below'))                          return 'Looking Down';
  if (l.includes('normal'))                         return 'Looking at Screen';
  return 'Gaze Violation';
}

function _isGazeDirectionEnabled(label) {
  if (currentQuestion.value?.question_type !== 'essay') return true;
  const normalized = String(label || '').toLowerCase();
  if (normalized.includes('above')) return activeExamRestrictions.value.gaze_above;
  if (normalized.includes('below')) return activeExamRestrictions.value.gaze_below;
  if (normalized.includes('left') && !normalized.includes('right')) {
    return activeExamRestrictions.value.gaze_left;
  }
  if (normalized.includes('right') && !normalized.includes('left')) {
    return activeExamRestrictions.value.gaze_right;
  }
  return true;
}

function _isGadgetDetectionEnabled() {
  return currentQuestion.value?.question_type !== 'essay'
    || activeExamRestrictions.value.gadgets;
}

function _gazePendingMatches(kind, label) {
  if (!_gazePending || _gazePending.kind !== kind) return false;
  if (kind === 'no_face') return true;
  return _gazePending.label === label;
}

function _setGazePending(kind, label) {
  _gazePending = { kind, label: label || '' };
  gazePendingActive.value = true;
}

function _clearGazePending() {
  _gazePending = null;
  gazePendingActive.value = false;
}

// ── Live direction violation timer ────────────────────────────────────────────
// Shows the classified direction immediately in the PiP camera and counts up
// toward the threshold — no waiting for a strike to be logged first.

/** label of the currently detected gaze direction (empty = looking at screen) */
const gazeCurrentDirection = ref('');
/** First confident horizontal result, shown before strike timing starts. */
const gazePreviewDirection = ref('');
const gazeDisplayDirection = computed(() => gazePreviewDirection.value || gazeCurrentDirection.value);
/** seconds elapsed since the direction was first detected */
const gazeElapsedSeconds = ref(0);
/** seconds required before a strike is logged for this direction */
const gazeThresholdSeconds = ref(0);
/** Date.now() of when the current violation was first detected */
let _gazeViolationStartTime = null;
/** setInterval handle for smooth elapsed-time display (~12 fps) */
let _gazeElapsedInterval = null;
/** setTimeout handle to prevent instant resets (UI hysteresis) */
let _gazeClearTimeout = null;

/** Start (or keep alive) the live direction timer for the PiP widget. */
function _startGazeViolationTimer(label, thresholdSeconds) {
  if (_gazeClearTimeout) {
    clearTimeout(_gazeClearTimeout);
    _gazeClearTimeout = null;
  }
  if (!_gazeViolationStartTime) {
    _gazeViolationStartTime = Date.now();
  }
  gazeCurrentDirection.value = label;
  gazeThresholdSeconds.value = thresholdSeconds || 5;
  if (!_gazeElapsedInterval) {
    _gazeElapsedInterval = setInterval(() => {
      if (_gazeViolationStartTime) {
        gazeElapsedSeconds.value = (Date.now() - _gazeViolationStartTime) / 1000;
      }
    }, 80);
  }
}

/** Clear the direction timer and reset all display state to normal.
 * If called from a violation-fired path, pass forceNow=true to reset
 * immediately without the debounce delay. */
function _clearGazeViolationTimer(forceNow = false) {
  // Always cancel any pending clear before scheduling a new one
  if (_gazeClearTimeout) {
    clearTimeout(_gazeClearTimeout);
    _gazeClearTimeout = null;
  }
  if (forceNow) {
    // Immediate reset — used when a violation just fired so the border
    // returns to green without a 1.5 s delay.
    _gazeViolationStartTime = null;
    if (_gazeElapsedInterval) {
      clearInterval(_gazeElapsedInterval);
      _gazeElapsedInterval = null;
    }
    gazeCurrentDirection.value = '';
    gazeElapsedSeconds.value = 0;
    gazeThresholdSeconds.value = 0;
  } else {
    // Wait a brief moment of continuous "normal" frames before fully resetting.
    // Long debounce made the old direction stick after looking back at the screen.
    _gazeClearTimeout = setTimeout(() => {
      _gazeViolationStartTime = null;
      if (_gazeElapsedInterval) {
        clearInterval(_gazeElapsedInterval);
        _gazeElapsedInterval = null;
      }
      gazeCurrentDirection.value = '';
      gazeElapsedSeconds.value = 0;  // ← explicitly zero out so the bar resets instantly
      gazeThresholdSeconds.value = 0;
      _gazeClearTimeout = null;
    }, 180);
  }
}

/** 0–1 progress toward the strike threshold. */
const gazeDirectionProgress = computed(() =>
  gazeThresholdSeconds.value
    ? Math.min(1, gazeElapsedSeconds.value / gazeThresholdSeconds.value)
    : 0,
);
/** Amber → orange → red as progress approaches 1. */
const gazeDirectionBarColor = computed(() => {
  const p = gazeDirectionProgress.value;
  if (p < 0.5) return '#f59e0b';
  if (p < 0.8) return '#f97316';
  return '#ef4444';
});
/** Arrow icon for the detected direction. */
const gazeDirectionIcon = computed(() => {
  const l = (gazeDisplayDirection.value || '').toLowerCase();
  if (l.includes('left'))  return '←';
  if (l.includes('right')) return '→';
  if (l.includes('above')) return '↑';
  if (l.includes('below')) return '↓';
  return '!';
});
/** Short, readable label shown in the PiP overlay. */
const gazeDirectionLabel = computed(() => _formalGazeLabel(gazeDisplayDirection.value));

// ── PiP border glow (replaces face bounding box) ─────────────────────────────
// Instead of a canvas bounding box (which was inaccurate and laggy),
// the entire PiP widget border changes color instantly to reflect gaze state.

// Track last known face state and suspicious label for border color.
const _gazeRawLabel = ref('');
const _gazeFaceDetected = ref(true);

/** Update label/face state from gaze API response (no bbox needed). */
function _updateGazeBbox(data) {
  _gazeRawLabel.value = data.label || '';
  _gazeFaceDetected.value = Boolean(data.face_detected);
}

/** Computed: border color driven reactively by the displayed direction and face state. */
const pipBorderColor = computed(() => {
  if (gazeDetectionStatus.value) return '#f59e0b';
  if (!_gazeFaceDetected.value || _gazeRawLabel.value === 'no_face') return '#ef4444'; // red — no face
  if (gazeDisplayDirection.value) {
    const l = gazeDisplayDirection.value.toLowerCase();
    if (l.includes('left') || l.includes('right')) return '#f97316';  // orange — sideways
    if (l.includes('above')) return '#a855f7';                         // purple — looking up
    if (l.includes('below')) return '#f59e0b';                         // amber — looking down
    return '#f97316';                                                   // orange — other violation
  }
  return '#34d399'; // green — normal
});

/** Computed: glow shadow matching border color. */
const pipBorderGlow = computed(() => {
  const c = pipBorderColor.value;
  if (c === '#34d399') return `0 0 0 2px ${c}, 0 0 12px rgba(52,211,153,0.45)`;
  if (c === '#f97316') return `0 0 0 2px ${c}, 0 0 14px rgba(249,115,22,0.55)`;
  if (c === '#a855f7') return `0 0 0 2px ${c}, 0 0 14px rgba(168,85,247,0.55)`;
  if (c === '#f59e0b') return `0 0 0 2px ${c}, 0 0 14px rgba(245,158,11,0.55)`;
  return `0 0 0 2px ${c}, 0 0 14px rgba(239,68,68,0.55)`; // red
});

function _startGazeBboxDraw() { /* no-op: border is CSS-driven */ }
function _stopGazeBboxDraw() {
  _gazeRawLabel.value = '';
  _gazeFaceDetected.value = true;
}

function _getProctoringVideoEl() {
  const examVid = examVideoEl.value;
  if (examVid?.videoWidth > 0) return examVid;
  const permVid = permVideoEl.value;
  if (permVid?.videoWidth > 0) return permVid;
  return examVid || permVid;
}

async function _captureProctoringSnapshot(caption = 'Periodic webcam capture', { eventId = null, examId = null } = {}) {
  const targetExamId = examId ?? takingExam.value?.id;
  if (!targetExamId) return false;

  let video = _getProctoringVideoEl();
  if (!video?.videoWidth) {
    await new Promise((r) => setTimeout(r, 200));
    video = _getProctoringVideoEl();
  }
  if (!video?.videoWidth) {
    console.warn('Proctoring capture skipped: webcam frame not ready');
    return false;
  }

  try {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return false;
    ctx.drawImage(video, 0, 0);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82));
    if (!blob) return false;
    const form = new FormData();
    form.append('image', blob, `webcam_${Date.now()}.jpg`);
    form.append('evidence_type', 'webcam');
    form.append('caption', caption);
    if (eventId) {
      form.append('event_id', String(eventId));
    }
    await api.post(`/api/student/exams/${targetExamId}/proctoring/evidence/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    if (!eventId && takingExam.value && !examTerminated.value) {
      await _logProctoringEvent('periodic_capture', {
        message: caption,
        source: 'webcam',
        severity: 'info',
      });
    }
    return true;
  } catch (err) {
    console.warn('Proctoring evidence upload failed:', err?.response?.data || err);
    return false;
  }
}

async function _captureBrowserScreen(examId, eventPromise, caption, requireAway = true) {
  const video = _screenShareVideo;
  const track = _screenShareStream?.getVideoTracks()[0];
  if (!examId || !track || track.readyState !== 'live' || (requireAway && !_isAway)) return false;
  try {
    // Read the monitor track directly because a hidden tab may stop painting
    // the preview video while screen sharing remains active.
    const blob = await captureSharedDisplayImage({
      track,
      video,
      doc: document,
      isAway: () => _isAway,
      requireAway,
    });
    if (!blob) return false;
    const form = new FormData();
    form.append('image', blob, `screen_switch_${Date.now()}.jpg`);
    form.append('evidence_type', 'screen');
    form.append('caption', caption);
    const eventId = await eventPromise;
    if (eventId) form.append('event_id', String(eventId));
    await api.post(`/api/student/exams/${examId}/proctoring/evidence/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 5000,
    });
    return true;
  } catch (err) {
    console.warn('Screen evidence upload failed:', err?.response?.data || err);
    return false;
  }
}

function _startProctoringCaptureTimer() {
  _stopProctoringCaptureTimer();
  _proctoringCaptureTimer = setInterval(() => {
    _captureProctoringSnapshot('Scheduled webcam snapshot during exam');
  }, PROCTORING_CAPTURE_INTERVAL_MS);
  setTimeout(() => _captureProctoringSnapshot('Exam session start snapshot'), 5000);
}

function _stopProctoringCaptureTimer() {
  if (_proctoringCaptureTimer) {
    clearInterval(_proctoringCaptureTimer);
    _proctoringCaptureTimer = null;
  }
}

async function _runGadgetDetection() {
  if (!_gadgetLoopActive || !takingExam.value || examTerminated.value || submitting.value) return;
  if (!_isGadgetDetectionEnabled()) {
    gadgetDetectionStatus.value = 'off for this question';
    _gadgetDetectionTimer = setTimeout(_runGadgetDetection, GADGET_IDLE_POLL_MS);
    return;
  }
  if (_gadgetDetectionInFlight) {
    _gadgetDetectionTimer = setTimeout(_runGadgetDetection, GADGET_IDLE_POLL_MS);
    return;
  }
  const video = _getProctoringVideoEl();
  if (!video || video.readyState < 2 || !video.videoWidth) {
    _gadgetDetectionTimer = setTimeout(_runGadgetDetection, GADGET_IDLE_POLL_MS);
    return;
  }

  _gadgetDetectionInFlight = true;
  const generation = _gadgetLoopGeneration;
  const frameW = Math.min(GADGET_FRAME_WIDTH, video.videoWidth);
  const frameH = Math.round((video.videoHeight / video.videoWidth) * frameW);
  try {
    const canvas = _gadgetCaptureCanvas || (_gadgetCaptureCanvas = document.createElement('canvas'));
    if (canvas.width !== frameW || canvas.height !== frameH) {
      canvas.width = frameW;
      canvas.height = frameH;
    }
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, frameW, frameH);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.7));
    if (!blob) return;
    if (generation !== _gadgetLoopGeneration || !_gadgetLoopActive) return;

    const form = new FormData();
    form.append('image', blob, `gadget_${Date.now()}.jpg`);
    form.append('question_id', String(currentQuestion.value?.id || ''));
    // Default api timeout (15s) is too short under gaze CPU load.
    const { data } = await api.post(
      `/api/student/exams/${takingExam.value.id}/proctoring/gadgets/`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 65000 },
    );
    if (generation !== _gadgetLoopGeneration || !_gadgetLoopActive) return;
    if (data.warming) {
      gadgetDetectionStatus.value = 'starting';
    } else {
      gadgetDetectionStatus.value = data.enabled === false
        ? 'off for this question'
        : (data.detected ?? Boolean(data.detections?.length)) ? 'detected' : 'active';
    }
    _gadgetFailureCount = 0;
    if (typeof data.warning_count === 'number') {
      gadgetWarningCount.value = data.warning_count;
    }
    const warningLimit = data.warning_limit ?? GADGET_WARNING_LIMIT;
    if (data.should_terminate) {
      const labels = [...new Set((data.detections || []).map(item => item.label))];
      proctoringWarning.value = {
        show: true,
        type: 'gadget',
        title: 'Exam Terminated',
        message: `${labels.join(' and ') || 'A prohibited device'} was detected ${gadgetWarningCount.value} times. Your exam has been terminated.`,
      };
      terminateReason.value = 'gadget';
      _terminateExam();
      return;
    }
    if (data.logged_event || data.confirmed) {
      const labels = [...new Set((data.detections || []).map(item => item.label))];
      const remaining = Math.max(0, warningLimit - gadgetWarningCount.value);
      proctoringWarning.value = {
        show: true,
        type: 'gadget',
        title: `Prohibited Gadget — Warning ${gadgetWarningCount.value} of ${warningLimit}`,
        message: `${labels.join(' and ') || 'A prohibited device'} was detected. Remove it from the camera view immediately. ${remaining} warning${remaining === 1 ? '' : 's'} remaining before exam termination.`,
      };
    }
  } catch (err) {
    if (generation !== _gadgetLoopGeneration || !_gadgetLoopActive) return;
    if (err?.response?.status === 429) {
      gadgetDetectionStatus.value = 'busy';
      return;
    }
    _gadgetFailureCount += 1;
    if (err?.response?.status === 503 || _gadgetFailureCount >= 2) {
      gadgetDetectionStatus.value = 'unavailable';
    }
    if (gadgetDetectionStatus.value === 'unavailable' && !_gadgetUnavailableNotified) {
      _gadgetUnavailableNotified = true;
      showToastMessage('Gadget scanning is unavailable. Check the server connection or contact your instructor.');
    }
  } finally {
    if (generation === _gadgetLoopGeneration) {
      _gadgetDetectionInFlight = false;
      if (_gadgetLoopActive) {
        const pollDelay = gadgetDetectionStatus.value === 'detected'
          ? GADGET_VISIBLE_POLL_MS
          : gadgetDetectionStatus.value === 'active'
            ? GADGET_ACTIVE_POLL_MS
            : gadgetDetectionStatus.value === 'unavailable'
              ? GADGET_ERROR_POLL_MS
              : GADGET_IDLE_POLL_MS;
        _gadgetDetectionTimer = setTimeout(
          _runGadgetDetection,
          pollDelay,
        );
      }
    }
  }
}

function _startGadgetDetectionTimer() {
  _stopGadgetDetectionTimer();
  _gadgetUnavailableNotified = false;
  _gadgetFailureCount = 0;
  gadgetDetectionStatus.value = 'starting';
  _gadgetLoopActive = true;
  _runGadgetDetection();
}

function _stopGadgetDetectionTimer() {
  _gadgetLoopActive = false;
  _gadgetLoopGeneration++;
  if (_gadgetDetectionTimer) {
    clearTimeout(_gadgetDetectionTimer);
    _gadgetDetectionTimer = null;
  }
  _gadgetDetectionInFlight = false;
  gadgetDetectionStatus.value = 'stopped';
  _gadgetCaptureCanvas = null;
}

async function _runGazeCheck() {
  if (!takingExam.value || examTerminated.value || submitting.value || _gazeCheckInFlight) return;
  const video = examVideoEl.value;
  if (!video || video.readyState < 2 || !video.videoWidth) return;

  _gazeCheckInFlight = true;
  try {
    // While WS is healthy, reuse its exact analyzed frame. HTTP handles counts
    // and absence policy without competing for another inference pass.
    const analyzed = _gazeWsActive ? _wsLatestFrame : null;
    if (_gazeWsActive && (!analyzed?.receipt || Date.now() - analyzed.receivedAt > 1500)) return;
    let blob;
    if (analyzed) {
      blob = _gazeFrameBlob(analyzed.image);
    } else {
      const canvas = document.createElement('canvas');
      canvas.width = GAZE_FRAME_WIDTH;
      canvas.height = Math.round((video.videoHeight / video.videoWidth) * GAZE_FRAME_WIDTH);
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.75));
    }
    if (!blob) return;
    const form = new FormData();
    form.append('image', blob, `gaze_${Date.now()}.jpg`);
    form.append('question_id', String(analyzed?.questionId || currentQuestion.value?.id || ''));
    form.append('record_strike', 'false');
    if (analyzed) {
      form.append('frame_receipt', analyzed.receipt);
      form.append('observe_only', 'true');
    }
    const { data } = await api.post(
      `/api/student/exams/${takingExam.value.id}/proctoring/gaze/`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );

    const conf = data.confidence ?? 0;
    const thresholds = {
      general: data.confidence_threshold ?? GAZE_CONFIDENCE_MIN,
      above: data.above_confidence_threshold ?? GAZE_ABOVE_CONFIDENCE_MIN,
      left: data.left_confidence_threshold ?? GAZE_LEFT_CONFIDENCE_MIN,
      right: data.right_confidence_threshold ?? GAZE_RIGHT_CONFIDENCE_MIN,
      below: data.below_confidence_threshold ?? GAZE_BELOW_CONFIDENCE_MIN,
    };
    const normalizedLabel = String(data.label || '').toLowerCase();
    const isNoFace = data.is_no_face === true
      || !data.face_detected
      || normalizedLabel === 'no_face'
      || normalizedLabel.includes('multiple_people');
    const directionEnabled = data.direction_enabled !== false
      && _isGazeDirectionEnabled(data.label);
    const holdSeconds = data.no_face_hold_seconds ?? GAZE_NO_FACE_HOLD_SECONDS;

    // Do not let the slower HTTP observer overwrite a newer WS result.
    if (!_gazeWsActive) {
      gazeDetectionStatus.value = '';
      _updateGazeBbox(
        !isNoFace && !directionEnabled
          ? { ...data, label: 'Normal', is_suspicious: false, is_normal: true }
          : data,
      );
    }

    if (isNoFace) {
      _notifyExamineeAbsent();
      faceAbsentSeconds.value = data.absent_seconds ?? 0;
      const nowOnHold = Boolean(data.hold_exam);
      if (nowOnHold && !_faceHoldSnapshotted) {
        _faceHoldSnapshotted = true;
        const holdEventId = data.logged_event?.id ?? null;
        await _captureProctoringSnapshot(
          `Face not visible â€” exam paused (${holdSeconds}s threshold)`,
          { eventId: holdEventId },
        );
      }
      examFaceHold.value = nowOnHold;

      if (typeof data.gaze_no_face_count === 'number') {
        gazeNoFaceCount.value = data.gaze_no_face_count;
      }

      if (data.logged_event && !data.evidence) {
        await _captureProctoringSnapshot('Face not visible to proctoring camera', {
          eventId: data.logged_event.id,
        });
      }

      if (data.should_terminate) {
        proctoringWarning.value = {
          show: true,
          type: 'gaze',
          title: 'Exam Terminated',
          message: 'Your exam was terminated because your face was not visible to the camera too many times.',
        };
        terminateReason.value = 'gaze';
        _terminateExam();
        return;
      }

      if (data.logged_event) {
        const fLimit = data.limits?.gaze_no_face ?? GAZE_NO_FACE_LIMIT;
        const remaining = Math.max(0, fLimit - gazeNoFaceCount.value);
        proctoringWarning.value = {
          show: true,
          type: 'gaze',
          title: 'Face Not Visible',
          message: `Return to the camera now. Warning ${gazeNoFaceCount.value} of ${fLimit} (${remaining} remaining before termination). After ${holdSeconds} seconds without your face, the exam will pause.`,
        };
      }
      if (!_gazeWsActive) _clearGazeViolationTimer(true); // face not visible → no direction
      return;
    }

    if (!directionEnabled) {
      _clearGazePending();
      _clearGazeViolationTimer(true);
      return;
    }

    _clearAbsenceAlert();
    examFaceHold.value = false;
    faceAbsentSeconds.value = 0;
    _faceHoldSnapshotted = false;

    if (data.pending_strike) {
      _setGazePending('violation', data.label || '');
    } else if (data.is_normal || !data.is_suspicious) {
      _clearGazePending();
    }

    // When WebSocket is down, HTTP responses drive the direction timer so
    // gaze still flags without relying on the WS loop.
    if (!_gazeWsActive) {
      if (data.pending_strike && data.is_suspicious) {
        _startGazeViolationTimer(data.label, data.threshold_seconds || 4);
      } else if (data.is_normal || !data.is_suspicious) {
        _clearGazeViolationTimer();
      }
    }
    if (data.logged_event && !_gazeWsActive) {
      // Strike just fired — reset WS timer to prevent double-counting in UI
      _gazeViolationStartTime = Date.now();
      gazeElapsedSeconds.value = 0;
    }

    if (!data.logged_event) {
      if (data.pending_strike && data.is_suspicious && _gazeConfidenceMet(data.label, conf, thresholds)) {
        gazePendingActive.value = true;
      }
      return;
    }

    _clearGazePending();

    if (typeof data.gaze_violation_count === 'number') {
      gazeViolationCount.value = data.gaze_violation_count;
    }
    if (typeof data.gaze_no_face_count === 'number') {
      gazeNoFaceCount.value = data.gaze_no_face_count;
    }

    if (data.logged_event && !data.evidence) {
      await _captureProctoringSnapshot(`Gaze violation: ${data.label || 'look-away'}`, {
        eventId: data.logged_event.id,
      });
    }

    if (data.should_terminate) {
      proctoringWarning.value = {
        show: true,
        type: 'gaze',
        title: 'Exam Terminated',
        message: 'Your exam was terminated because you looked away from the screen too many times.',
      };
      terminateReason.value = 'gaze';
      _terminateExam();
      return;
    }

    if (Date.now() - _lastGazeWarningAt < GAZE_WARNING_COOLDOWN_MS) return;

    // When the WebSocket loop is active, it already shows the gaze violation popup.
    // Skip the HTTP popup for direction violations to prevent duplicate notifications.
    // (No-face violations are handled by the absence alert path, not here.)
    if (_gazeWsActive && data.logged_event && !data.is_no_face) {
      _lastGazeWarningAt = Date.now(); // mark as warned so cooldown is respected
      return;
    }

    _lastGazeWarningAt = Date.now();
    const label = data.label || 'Away from screen';
    const pct = Math.round(conf * 100);
    const vLimit = data.limits?.gaze_violation ?? GAZE_VIOLATION_LIMIT;

    proctoringWarning.value = {
      show: true,
      type: 'gaze',
      title: 'Look at Your Screen',
      message: `Gaze: ${label}. Warning ${gazeViolationCount.value} of ${vLimit} (${vLimit - gazeViolationCount.value} remaining before termination).`,
    };

    // Keep detection running while the warning is visible. The server-side
    // cooldown prevents duplicate strikes without introducing a blind period.
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || 'Gaze check failed';
    console.warn('Gaze check failed:', msg);
    if (err?.response?.status === 503) {
      showToastMessage('Gaze AI is unavailable on the server. Head movement checks are paused.');
    }
  } finally {
    _gazeCheckInFlight = false;
  }
}

// Self-scheduling async gaze loop — runs continuously while exam is active.
// Each iteration reschedules itself GAZE_CHECK_INTERVAL_MS after it FINISHES,
// so slow network calls never stack up or cause a backlog.
const GAZE_MIN_RESCHEDULE_MS = 20; // aggressively reduced to ensure immediate next frame
let _gazeLoopActive = false;

async function _gazeLoop() {
  if (!_gazeLoopActive) return;
  const t0 = Date.now();
  await _runGazeCheck();
  if (!_gazeLoopActive) return;
  const elapsed = Date.now() - t0;
  const interval = _gazeWsActive ? GAZE_CHECK_INTERVAL_MS : GAZE_HTTP_FALLBACK_INTERVAL_MS;
  const delay = Math.max(GAZE_MIN_RESCHEDULE_MS, interval - elapsed);
  _gazeCheckTimer = setTimeout(_gazeLoop, delay);
}

function _startGazeCheckTimer() {
  _stopGazeCheckTimer();
  _lastGazeWarningAt = 0;
  _clearGazePending();
  _gazeLoopActive = true;
  _startGazeWsLoop();
  // Start bbox canvas loop immediately so it's ready to paint the instant
  // the first video frame arrives (videoWidth becomes non-zero).
  _startGazeBboxDraw();

  // Fire the first gaze API check as soon as the video has an actual frame.
  // We listen for 'loadeddata' (readyState → 2) which fires the moment the
  // first frame is decoded and available.  'timeupdate' is a safety fallback
  // on some browsers where 'loadeddata' may have already fired before we
  // attached this listener.  A hard cap of 2 s prevents hanging if neither
  // event fires (e.g. stream not yet piped in).
  let _firstCheckDone = false;
  function _fireFirstCheck() {
    if (_firstCheckDone || !_gazeLoopActive) return;
    _firstCheckDone = true;
    const vid = examVideoEl.value;
    if (vid) {
      vid.removeEventListener('loadeddata', _fireFirstCheck);
      vid.removeEventListener('timeupdate', _fireFirstCheck);
    }
    if (_gazeLoopActive) _gazeLoop();
  }

  const vid = examVideoEl.value;
  if (vid && vid.readyState >= 2 && vid.videoWidth > 0) {
    // Video already has frames (e.g. stream was attached before this call)
    _gazeLoop();
  } else if (vid) {
    vid.addEventListener('loadeddata', _fireFirstCheck, { once: true });
    vid.addEventListener('timeupdate', _fireFirstCheck, { once: true });
    // Hard cap: give up waiting after 2 s and check anyway
    _gazeCheckTimer = setTimeout(_fireFirstCheck, 2000);
  } else {
    // Fallback: video ref not mounted yet, use original short delay
    _gazeCheckTimer = setTimeout(() => { if (_gazeLoopActive) _gazeLoop(); }, GAZE_FIRST_CHECK_MS);
  }
}

function _stopGazeCheckTimer() {
  _gazeLoopActive = false;
  if (_gazeCheckTimer) {
    clearTimeout(_gazeCheckTimer);
    _gazeCheckTimer = null;
  }
  _gazeCheckInFlight = false;
  _clearGazePending();
  _stopGazeWsLoop();
  _clearGazeViolationTimer();
  _stopGazeBboxDraw();
  examFaceHold.value = false;
  faceAbsentSeconds.value = 0;
  _faceHoldSnapshotted = false;
  _clearAbsenceAlert();
  _stopGadgetDetectionTimer();
}

// ── WebSocket Gaze Loop (Real-time UI + violation timing) ───────────────────
// The WS loop samples as soon as the previous inference result arrives
// (normally about every 80ms) and is used for:
//   1. Instant UI feedback (direction indicator, border color)
//   2. Violation timing — after 4s of continuous suspicious frames, log to DB
// This avoids the slow HTTP-based timer (which added 7+ seconds of delay due
// to AI processing time per HTTP call).
let _gazeWs = null;
let _gazeWsActive = false;
let _wsPendingFrame = null;
let _wsLatestFrame = null;
let _wsFrameId = 0;
let _wsHasResult = false;
let _wsLastAcceptedAt = null;
let _wsResponseTimeout = null;
let _wsSendTimer = null;
let _wsCaptureCanvas = null;
let _wsCloseCause = '';
const WS_CONNECT_TIMEOUT_MS = 12000;
const WS_FIRST_RESULT_TIMEOUT_MS = 20000;
const WS_RESPONSE_TIMEOUT_MS = 12000;
const WS_MAX_RESULT_AGE_MS = 2500;
const WS_MAX_STREAK_GAP_MS = 1500;

function _gazeFrameBlob(image) {
  const bytes = Uint8Array.from(atob(image.split(',')[1]), c => c.charCodeAt(0));
  return new Blob([bytes], { type: 'image/jpeg' });
}

function _scheduleWsFrame(delay = GAZE_WS_INTERVAL_MS) {
  clearTimeout(_wsSendTimer);
  _wsSendTimer = setTimeout(_sendWsFrame, delay);
}

function _expireWsGazeStreak(now) {
  if (_wsLastAcceptedAt === null || now - _wsLastAcceptedAt <= WS_MAX_STREAK_GAP_MS) return;
  _wsLastAcceptedAt = null;
  _wsViolationStartTime = null;
  _wsNormalStartTime = null;
  _wsNormalConsecutive = 0;
  _wsMultipleFacesStartTime = null;
  _wsSuspiciousFrame = null;
  gazePreviewDirection.value = '';
  _clearGazeViolationTimer(true);
}

// WS violation timing state
let _wsViolationStartTime  = null;   // when current violation streak started (ms)
let _wsViolationLabel      = '';      // most recent suspicious label
let _wsViolationFired      = false;   // prevent double-firing within same streak
let _wsNormalStartTime     = null;    // when current normal streak started (ms)
let _wsNormalConsecutive   = 0;       // consecutive Normal frames — require >=2 before resetting violation timer
// Exact classified JPEG and its signed result, retained for evidence.
let _wsSuspiciousFrame = null;
let _wsViolationCooldownEnd = 0;     // timestamp before which a new timer cannot start
let _wsNeedNormalReset     = false;  // student must look at camera before next timer
let _wsMultipleFacesStartTime = null; // timer for multiple-people detection
const WS_VIOLATION_MS         = 4000;  // 4s of suspicious frames ≈ 4-5s real-world look-away
const WS_MULTIPLE_FACES_MS    = 3000;  // 3s of multiple faces before flagging
const WS_NORMAL_CLEAR_MS      = 600;   // require ~600ms of sustained Normal before fully resetting timer
const WS_NORMAL_GRACE_FRAMES  = 2;     // consecutive Normal frames before resetting violation timer (was 3)
const WS_VIOLATION_COOLDOWN_MS = 3000; // hard cooldown after firing before timer can restart

function _startGazeWsLoop() {
  if (_gazeWsActive || (_gazeWs && _gazeWs.readyState < 2) || !takingExam.value || examTerminated.value || submitting.value) return;
  gazeDetectionStatus.value = 'Connecting';
  _wsViolationStartTime   = null;
  _wsViolationLabel       = '';
  _wsViolationFired       = false;
  _wsNormalStartTime      = null;
  _wsNormalConsecutive    = 0;
  _wsViolationCooldownEnd = 0;
  _wsNeedNormalReset = false;
  _wsMultipleFacesStartTime = null;
  _wsSuspiciousFrame       = null;
  gazePreviewDirection.value = '';
  _wsHasResult = false;
  _wsLastAcceptedAt = null;
  _wsCloseCause = '';

  const examId = takingExam.value.id;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const backendHost = new URL(backendBaseUrl).host;
  const token = localStorage.getItem('access_token') || '';
  
  _gazeWs = new WebSocket(`${protocol}//${backendHost}/ws/student/exams/${examId}/proctoring/gaze/?token=${token}`);
  
  const socket = _gazeWs;
  _wsResponseTimeout = setTimeout(() => {
    _wsCloseCause = 'connection timeout';
    socket.close();
  }, WS_CONNECT_TIMEOUT_MS);
  _gazeWs.onopen = () => {
    if (_gazeWs !== socket) return;
    clearTimeout(_wsResponseTimeout);
    _gazeWsActive = true;
    gazeDetectionStatus.value = 'Starting AI';
    _sendWsFrame();
  };
  
  _gazeWs.onmessage = (event) => {
    if (!_gazeWsActive || _gazeWs !== socket) return;
    clearTimeout(_wsResponseTimeout);
    const analyzedFrame = _wsPendingFrame;
    _wsPendingFrame = null;
    try {
      const data = JSON.parse(event.data);
      if (data.error) {
        _wsCloseCause = 'server inference error';
        socket.close();
        return;
      }
      const maxResultAge = _wsHasResult
        ? WS_MAX_RESULT_AGE_MS
        : WS_FIRST_RESULT_TIMEOUT_MS;
      if (!analyzedFrame || data.frame_id !== analyzedFrame.id) {
        _wsViolationStartTime = null;
        _clearGazeViolationTimer(true);
        _wsCloseCause = 'unmatched frame response';
        socket.close();
        return;
      }
      if (data.busy) {
        // The worker is occupied. The next attempt captures a fresh image;
        // never apply the old frame or treat this as an inference failure.
        _expireWsGazeStreak(Date.now());
        gazePreviewDirection.value = '';
        gazeDetectionStatus.value = 'AI busy';
        _scheduleWsFrame(GAZE_WS_BUSY_RETRY_MS);
        return;
      }
      if (!data.frame_receipt) {
        _wsCloseCause = data.error ? 'server inference error' : 'missing frame receipt';
        socket.close();
        return;
      }
      if (Date.now() - analyzedFrame.capturedAt > maxResultAge) {
        // Slow inference is not a broken connection. Discard the old result so
        // it cannot affect strikes, then sample a fresh frame on this socket.
        _wsViolationStartTime = null;
        _clearGazeViolationTimer(true);
        gazePreviewDirection.value = '';
        _wsLatestFrame = null;
        _wsLastAcceptedAt = null;
        _wsHasResult = true;
        gazeDetectionStatus.value = 'AI delayed';
        _scheduleWsFrame();
        return;
      }
      gazeDetectionStatus.value = '';
      const now = Date.now();
      _expireWsGazeStreak(now);
      _wsLastAcceptedAt = now;
      _wsHasResult = true;
      _wsLatestFrame = { ...analyzedFrame, receipt: data.frame_receipt, receivedAt: now };

      // ── (A) No face / Multiple faces ──────────────────────────────────
      // Check both is_no_face flag AND label directly (in case flag is missing)
      const wsLabel = (data.label || '').toLowerCase();
      const isAbsenceFrame = data.is_no_face === true
        || !data.face_detected
        || wsLabel === 'no_face'
        || wsLabel.includes('multiple_people');
      const directionEnabled = data.direction_enabled !== false
        && _isGazeDirectionEnabled(data.label);
      gazePreviewDirection.value = !isAbsenceFrame && directionEnabled
        && data.stabilizing && _isLeftRightLabel(data.label)
        ? data.label : '';
      _updateGazeBbox(
        !isAbsenceFrame && !directionEnabled
          ? { ...data, label: 'Normal', is_suspicious: false, is_normal: true }
          : data,
      );
      if (isAbsenceFrame) {
        _wsNormalStartTime    = null;
        _wsViolationStartTime = null;

        if (wsLabel.includes('multiple')) {
          // ── Multiple faces: show indicator + wait 3s before firing popup ──
          _startGazeViolationTimer('multiple_people', 3); // shows 🚫 indicator + 3s progress bar

          if (!_wsMultipleFacesStartTime) {
            _wsMultipleFacesStartTime = now;
          }

          if ((now - _wsMultipleFacesStartTime) >= WS_MULTIPLE_FACES_MS && !proctoringWarning.value.show) {
            _wsMultipleFacesStartTime = null;
            _clearGazeViolationTimer();
            proctoringWarning.value = {
              show: true,
              type: 'gaze',
              title: 'Multiple Faces Detected',
              message: 'Only you should be visible to the camera during this exam. Please ensure no other individuals are in the camera view.',
            };
            void _logProctoringEvent('warning_shown', {
              message: 'Multiple-faces warning displayed during the exam',
              source: 'multiple_faces_notice',
              metadata: { warning_type: 'multiple_faces' },
              severity: 'warning',
            });
          }
        } else {
          // Plain no_face: clear the indicator, HTTP handles strike counting
          _clearGazeViolationTimer();
          _wsMultipleFacesStartTime = null;
        }

        _scheduleWsFrame();
        return;
      }

      // Restrictions are quiz-wide. A disabled direction must never start a
      // browser timer even if a stale socket result marks it suspicious.
      if (!directionEnabled) {
        _wsNormalConsecutive = WS_NORMAL_GRACE_FRAMES;
        _wsNormalStartTime = now;
        _wsViolationStartTime = null;
        _wsViolationLabel = '';
        _wsSuspiciousFrame = null;
        _clearGazeViolationTimer(true);
        _scheduleWsFrame();
        return;
      }

      // ── (B) Suspicious gaze direction ─────────────────────────────
      if (data.is_suspicious) {
        _wsNormalStartTime = null;
        _wsNormalConsecutive = 0;  // reset grace period counter on any suspicious frame
        // Block new timer if: in hard cooldown OR student hasn't looked at camera since last violation
        const inCooldown = now < _wsViolationCooldownEnd || _wsNeedNormalReset;

        _startGazeViolationTimer(data.label, 4);
        if (!inCooldown) {

          if (!_wsViolationStartTime) {
            _wsViolationStartTime = now;
            _wsViolationFired = false;
          }
          _wsSuspiciousFrame = _wsLatestFrame;
          _wsViolationLabel = data.label;

          if (_wsViolationStartTime && !_wsViolationFired && (now - _wsViolationStartTime) >= WS_VIOLATION_MS) {
            _wsViolationFired       = true;
            _wsViolationCooldownEnd = now + WS_VIOLATION_COOLDOWN_MS;
            _wsNeedNormalReset      = true;  // must see normal frames before next timer
            _wsViolationStartTime   = null;
            const labelToRecord = _wsViolationLabel;
            _wsViolationLabel = '';

            // Keep showing the actual direction while the strike is saved.

            // Immediate popup — show before HTTP responds
            const estimatedCount = (gazeViolationCount.value || 0) + 1;
            proctoringWarning.value = {
              show: true,
              type: 'gaze',
              title: 'Gaze Violation Detected',
              message: `You looked away from your screen (${_formalGazeLabel(labelToRecord)}). Warning ${estimatedCount} of ${GAZE_VIOLATION_LIMIT} — please keep your eyes on the monitor.`,
            };
            // HTTP call logs the strike and updates exact count
            _recordWsViolation(labelToRecord);
          }
        } else {
          // Cooldown suppresses duplicate strikes, not the live direction.
          _wsViolationStartTime = null;
        }

      } else if (data.is_normal || !data.label || wsLabel.includes('normal')) {
        // Looking at screen: count consecutive Normal frames.
        // Only clear the violation timer and reset the start time after
        // WS_NORMAL_GRACE_FRAMES frames (~360ms) — a single momentary
        // glance-back in the middle of a look-away should NOT cancel the timer.
        _wsNormalConsecutive++;
        if (_wsNormalConsecutive >= WS_NORMAL_GRACE_FRAMES) {
          _clearGazeViolationTimer(true);
          _wsViolationStartTime = null;
          _wsViolationLabel = '';
          _wsSuspiciousFrame = null;       // clear stale evidence blob
        }

        if (!_wsNormalStartTime) {
          _wsNormalStartTime = now;
        } else if (now - _wsNormalStartTime >= WS_NORMAL_CLEAR_MS) {
          // Student has been looking at screen for WS_NORMAL_CLEAR_MS ms: full reset
          _wsViolationStartTime     = null;
          _wsViolationLabel         = '';
          _wsViolationFired         = false;
          _wsNormalStartTime        = null;
          _wsNormalConsecutive      = 0;
          _wsNeedNormalReset        = false;  // allow new violation timer
          _wsMultipleFacesStartTime = null;   // reset multiple-faces timer
          _wsViolationCooldownEnd   = 0;
          _wsSuspiciousFrame         = null;   // clear stale evidence blob
        }
      } else if (data.stabilizing) {
        // The first confident horizontal result is useful visual feedback even
        // though a second frame must confirm it before strike timing begins.
        // gazePreviewDirection drives the badge while the strike timer stays idle.
        _wsNormalStartTime = null;
      } else {
        _clearGazeViolationTimer(true);
        _wsViolationStartTime = null;
        _wsSuspiciousFrame = null;
      }

      _scheduleWsFrame();
    } catch(e) {
      console.error('[GazeWS] handler error:', e);
      _scheduleWsFrame();

    }
  };
  
  _gazeWs.onclose = (event) => {
    if (_gazeWs !== socket) return;
    console.warn('[GazeWS] closed:', {
      code: event?.code,
      reason: event?.reason,
      cause: _wsCloseCause || 'connection closed',
    });
    clearTimeout(_wsResponseTimeout);
    clearTimeout(_wsSendTimer);
    _wsPendingFrame = null;
    _wsLatestFrame = null;
    _wsLastAcceptedAt = null;
    _wsViolationStartTime = null;
    gazePreviewDirection.value = '';
    _clearGazeViolationTimer(true);
    _gazeWsActive = false;
    gazeDetectionStatus.value = 'Reconnecting';
    if (takingExam.value && !examTerminated.value && !submitting.value) {
      setTimeout(() => {
        if (!_gazeWsActive && takingExam.value && !examTerminated.value) {
          _startGazeWsLoop();
        }
      }, 1500);
    }
  };

  _gazeWs.onerror = () => {
    _wsCloseCause = 'socket error';
    try { socket.close(); } catch (_) { /* ignore */ }
  };
}

/** Called by the WS timer after 4s of suspicious frames — logs the violation via HTTP. */
async function _recordWsViolation(label) {
  if (!takingExam.value || examTerminated.value || !_isGazeDirectionEnabled(label)) return;

  try {
    // This is the JPEG that produced the WS label, not a later webcam frame.
    const analyzed = _wsSuspiciousFrame;
    _wsSuspiciousFrame = null;
    if (!analyzed?.receipt) return;
    const blob = _gazeFrameBlob(analyzed.image);
    const form = new FormData();
    form.append('image', blob, `gaze_ws_${analyzed.id}.jpg`);
    form.append('frame_receipt', analyzed.receipt);
    form.append('record_strike', 'true');
    form.append('forced_label', label);
    form.append('question_id', String(analyzed.questionId || currentQuestion.value?.id || ''));

    const { data } = await api.post(
      `/api/student/exams/${takingExam.value.id}/proctoring/gaze/`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );

    // Sync counts
    if (typeof data.gaze_violation_count === 'number') gazeViolationCount.value = data.gaze_violation_count;
    if (typeof data.gaze_no_face_count  === 'number') gazeNoFaceCount.value  = data.gaze_no_face_count;

    if (data.logged_event) {
      _clearGazePending();
      const vLimit    = data.limits?.gaze_violation ?? GAZE_VIOLATION_LIMIT;
      const remaining = Math.max(0, vLimit - gazeViolationCount.value);
      // Only update the popup if it is STILL showing.
      // If the student already dismissed it, do NOT re-show — that causes the
      // "duplicate" popup the user sees 1-2s after the first notification.
      if (proctoringWarning.value.show && proctoringWarning.value.type === 'gaze') {
        proctoringWarning.value = {
          show: true,
          type: 'gaze',
          title: 'Gaze Violation Detected',
          message: `You looked away from your screen (${_formalGazeLabel(label)}). Warning ${gazeViolationCount.value} of ${vLimit} — ${remaining} remaining before exam termination.`,
        };
      }
      if (!data.evidence) {
        await _captureProctoringSnapshot(`Gaze violation: ${_formalGazeLabel(label)}`, { eventId: data.logged_event.id });
      }
    }

    if (data.should_terminate) {
      proctoringWarning.value = {
        show: true, type: 'gaze', title: 'Exam Terminated',
        message: 'Your exam was terminated because you looked away from the screen too many times.',
      };
      terminateReason.value = 'gaze';
      _terminateExam();
    }
  } catch (err) {
    console.warn('WS violation record failed:', err?.response?.data || err);
    _wsNeedNormalReset = false;
    _wsViolationFired = false;
  }
}

async function _sendWsFrame() {
  if (!_gazeWsActive || !_gazeWs || _gazeWs.readyState !== WebSocket.OPEN || submitting.value || _wsPendingFrame) return;
  const video = examVideoEl.value;
  if (!video || video.readyState < 2 || !video.videoWidth) {
    _scheduleWsFrame();
    return;
  }
  
  const canvas = _wsCaptureCanvas || (_wsCaptureCanvas = document.createElement('canvas'));
  const SEND_W = GAZE_FRAME_WIDTH;
  const SEND_H = Math.round((video.videoHeight / video.videoWidth) * SEND_W);
  if (canvas.width !== SEND_W || canvas.height !== SEND_H) {
    canvas.width = SEND_W;
    canvas.height = SEND_H;
  }
  const ctx = canvas.getContext('2d', { alpha: false });
  if (!ctx) return;
  ctx.drawImage(video, 0, 0, SEND_W, SEND_H);
  
  // Use canvas.toDataURL for base64 string
  const base64Image = canvas.toDataURL('image/jpeg', 0.75);
  const socket = _gazeWs;
  _wsPendingFrame = {
    id: ++_wsFrameId,
    image: base64Image,
    capturedAt: Date.now(),
    questionId: currentQuestion.value?.id || null,
  };
  _wsResponseTimeout = setTimeout(() => {
    if (_gazeWs === socket) {
      _wsCloseCause = 'inference response timeout';
      socket.close();
    }
  }, _wsHasResult ? WS_RESPONSE_TIMEOUT_MS : WS_FIRST_RESULT_TIMEOUT_MS);
  socket.send(JSON.stringify({
    image: base64Image,
    frame_id: _wsPendingFrame.id,
    question_id: _wsPendingFrame.questionId,
  }));
}

function _stopGazeWsLoop() {
  gazeDetectionStatus.value = '';
  clearTimeout(_wsResponseTimeout);
  clearTimeout(_wsSendTimer);
  _wsPendingFrame = null;
  _wsLatestFrame = null;
  _wsLastAcceptedAt = null;
  gazePreviewDirection.value = '';
  _wsCaptureCanvas = null;
  _wsHasResult = false;
  _gazeWsActive = false;
  _wsViolationStartTime = null;
  _wsViolationLabel = '';
  _wsViolationFired = false;
  _wsNormalStartTime = null;
  _wsNormalConsecutive = 0;
  _wsSuspiciousFrame = null;
  if (_gazeWs) {
    const socket = _gazeWs;
    _gazeWs = null;
    socket.close();
  }
}

// Results modal (separate from taking modal)
const resultsModal = ref(null);
const resultsData = ref({});
const resultsLoading = ref(false);

// --- Camera / Mic permission state ---
const showPermissionModal = ref(false);
const permissionLoading = ref(false);
const permissionError = ref("");
const mediaStreamActive = ref(false);
let activeMediaStream = null;
let pendingExam = null;
const permVideoEl = ref(null);
const examVideoEl = ref(null);
const precheckFaceVisible = ref(false);
const precheckStatus = ref('checking');
const precheckMessage = computed(() => ({
  checking: 'Checking your face position. Keep your face centered and well lit.',
  ready: 'Face clearly detected. You can continue.',
  too_far: 'Too far or face not detected. Move closer to the camera and check the lighting.',
  multiple_faces: 'More than one face detected. Only you should be visible.',
  unavailable: 'Face check unavailable. Retry the check before continuing.',
})[precheckStatus.value]);
let _precheckTimer = null;
let _precheckController = null;
let _precheckRunId = 0;
let _precheckReadyStreak = 0;

// --- Face Verification state ---
const fvShow        = ref(false);
const fvStep        = ref('verifying'); // 'verifying' | 'success' | 'failed' | 'no-photo'
const fvAttemptsLeft = ref(2);
const fvErrorMsg    = ref('');
const FV_MAX_ATTEMPTS = 3;
const timelineWindowDays = ref("3650");
const timelineSearch = ref("");
const courseFilter = ref("all");
const courseSearch = ref("");
const courseSort = ref("name_asc");
const courseView = ref("card");

const displayedCourses = computed(() => {
  const query = courseSearch.value.toLowerCase();
  let rows = [...(subjects.value || [])];
  if (query) {
    rows = rows.filter((s) =>
      `${s.code} ${s.name}`.toLowerCase().includes(query),
    );
  }
  if (courseSort.value === "name_desc") {
    rows.sort((a, b) => String(b.name || "").localeCompare(String(a.name || "")));
  } else {
    rows.sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
  }
  return rows;
});

const currentTime = ref("");
const currentDate = ref("");
let timeInterval = null;

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  currentDate.value = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
};

const api = axios.create({
  baseURL: backendBaseUrl,
  timeout: 15000,
});

let refreshInFlight = null;

async function refreshAccessToken() {
  if (refreshInFlight) return refreshInFlight;
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    await performLogout();
    throw new Error("No refresh token available.");
  }
  refreshInFlight = axios
    .post(`${backendBaseUrl}/api/auth/token/refresh/`, { refresh: refreshToken })
    .then((res) => {
      const nextAccess = res?.data?.access;
      if (!nextAccess) {
        throw new Error("No access token from refresh endpoint.");
      }
      localStorage.setItem("access_token", nextAccess);
      return nextAccess;
    })
    .catch(async (err) => {
      await performLogout();
      throw err;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

api.interceptors.request.use((config) => {
  const access = localStorage.getItem("access_token");
  if (access) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (err) => {
    const status = err?.response?.status;
    const original = err?.config;
    if (status === 401 && original && !original._retry) {
      original._retry = true;
      const nextAccess = await refreshAccessToken();
      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${nextAccess}`;
      return api(original);
    }
    throw err;
  },
);

async function getWithRetry(url, config = {}, retries = 2) {
  try {
    return await api.get(url, config);
  } catch (err) {
    const status = err?.response?.status;
    const isRetriable = !status || [408, 429, 500, 502, 503, 504].includes(status);
    if (retries > 0 && isRetriable) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      return getWithRetry(url, config, retries - 1);
    }
    throw err;
  }
}

async function fetchMySubjects() {
  subjectsLoading.value = true;
  subjectsError.value = "";
  try {
    const response = await getWithRetry("/api/student/subjects/");
    subjects.value = response.data.subjects || [];
  } catch (err) {
    subjectsError.value = err?.response?.data?.error || "Unable to load subjects.";
  } finally {
    subjectsLoading.value = false;
  }
}

function formatDate(raw) {
  if (!raw) return "No date set";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return "No date set";
  return d.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
}

function formatAvailability(exam) {
  const startString = exam.available_from ? formatDate(exam.available_from) : 'Open';
  const endString = exam.due_at ? formatDate(exam.due_at) : 'No limit';
  return `${startString} - ${endString}`;
}

function toAbsoluteFileUrl(fileUrl) {
  if (!fileUrl) return "";
  if (String(fileUrl).startsWith("http://") || String(fileUrl).startsWith("https://")) return fileUrl;
  return `${backendBaseUrl}${fileUrl}`;
}

let examFetchGeneration = 0;

async function fetchMyExams(background = false) {
  const generation = ++examFetchGeneration;
  if (!background) examsLoading.value = true;
  if (!background) examsError.value = "";
  try {
    const response = await getWithRetry("/api/student/exams/");
    if (generation !== examFetchGeneration) return;
    exams.value = [...(response.data.exam_sets || [])].sort(compareExamsNewestFirst);
    examsError.value = "";
  } catch (err) {
    if (generation !== examFetchGeneration) return;
    if (!background) examsError.value = err?.response?.data?.error || "Unable to load exams.";
  } finally {
    if (generation === examFetchGeneration) examsLoading.value = false;
  }
}

let examUpdatesSocket = null;
let examUpdatesRetryTimer = null;
let examUpdatesStopped = false;

function examUpdatesTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return !payload.exp || payload.exp * 1000 <= Date.now() + 10000;
  } catch {
    return true;
  }
}

async function connectExamUpdates() {
  if (examUpdatesStopped || examUpdatesSocket) return;
  let token = localStorage.getItem('access_token');
  if (!token) return;
  if (examUpdatesTokenExpired(token)) {
    try {
      token = await refreshAccessToken();
    } catch {
      return;
    }
    if (examUpdatesStopped || examUpdatesSocket) return;
  }

  const url = new URL('/ws/student/exams/updates/', backendBaseUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('token', token);
  const socket = new WebSocket(url.toString());
  examUpdatesSocket = socket;

  socket.onopen = () => {
    if (examUpdatesSocket === socket) fetchMyExams(true);
  };
  socket.onmessage = (event) => {
    if (examUpdatesSocket !== socket) return;
    try {
      if (JSON.parse(event.data).type === 'exam_published') fetchMyExams(true);
    } catch {
      // Ignore malformed update messages.
    }
  };
  socket.onclose = async (event) => {
    if (examUpdatesSocket !== socket) return;
    examUpdatesSocket = null;
    if (examUpdatesStopped || event.code === 4403) return;
    if (event.code === 4401) {
      try {
        await refreshAccessToken();
      } catch {
        return;
      }
    }
    examUpdatesRetryTimer = setTimeout(connectExamUpdates, 3000);
  };
}

function stopExamUpdates() {
  examUpdatesStopped = true;
  clearTimeout(examUpdatesRetryTimer);
  if (examUpdatesSocket) {
    examUpdatesSocket.close();
    examUpdatesSocket = null;
  }
  document.removeEventListener('visibilitychange', refreshExamsWhenVisible);
}

function refreshExamsWhenVisible() {
  if (document.visibilityState !== 'visible') return;
  fetchMyExams(true);
  connectExamUpdates();
}

const activeNav = computed(() => {
  if (route.path.startsWith("/student/courses")) return "courses";
  if (route.path.startsWith("/student/settings")) return "settings";
  return "dashboard";
});
const isCourseDetailRoute = computed(() => Boolean(route.params.courseId));
const pageTitle = computed(() => {
  if (activeNav.value === "dashboard") return "Dashboard";
  if (activeNav.value === "courses") return "My Courses";
  if (activeNav.value === "settings") return "Profile";
  return "AI-Vigilation";
});

const selectedCourseLabel = computed(() => {
  if (!selectedSubjectId.value) return "";
  const found = subjects.value.find((s) => Number(s.id) === Number(selectedSubjectId.value));
  return found ? `${found.code} - ${found.name}` : "";
});

const selectedCourse = computed(() => {
  if (!selectedSubjectId.value) return null;
  return subjects.value.find((s) => Number(s.id) === Number(selectedSubjectId.value)) || null;
});

const selectedCourseExams = computed(() =>
  exams.value
    .filter((exam) => Number(exam.subject_id) === Number(selectedSubjectId.value))
    .sort(compareExamsNewestFirst),
);

function formatTimeOnly(raw) {
  if (!raw) return "23:59";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return "23:59";
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute:'2-digit' });
}

function formatDisplayTitle(title) {
  if (!title || typeof title !== 'string') return '';
  return title
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1 $2')
    .replace(/\bchechpoint\b/gi, 'Checkpoint')
    .replace(/\bintergrative\b/gi, 'Integrative')
    .trim();
}

function formatFullDate(raw) {
  if (!raw) return "";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return "";
  const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true };
  return d.toLocaleString('en-GB', options);
}

function formatDuration(startStr, endStr) {
  if (!startStr || !endStr) return "N/A";
  const ms = new Date(endStr).getTime() - new Date(startStr).getTime();
  if (ms < 0) return "0 secs";
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  if (m === 0) return `${s} secs`;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    const rm = m % 60;
    return `${h} hr ${rm} mins`;
  }
  return `${m} mins ${s} secs`;
}

const filteredDueExamTimeline = computed(() => {
  const now = Date.now();
  const withinDays = Number(timelineWindowDays.value || 3650);
  const query = timelineSearch.value.toLowerCase();
  let rows = (exams.value || []).filter((exam) => {
    if (!studentExamOnDashboard(exam, { now, withinDays })) return false;
    if (!query) return true;
    return (
      String(exam?.title || "").toLowerCase().includes(query) ||
      String(exam?.subject_name || "").toLowerCase().includes(query) ||
      String(exam?.subject_code || "").toLowerCase().includes(query)
    );
  });

  return rows.sort(compareExamsNewestFirst);
});

function getExamStatus(exam) {
  if (exam?.terminated) return "Terminated";
  if (exam?.is_done) return "Done";
  const now = Date.now();
  const startTs = new Date(exam?.available_from || 0).getTime();
  const dueTs = exam?.due_at ? new Date(exam.due_at).getTime() : NaN;

  if (exam?.available_from && startTs > now) return "Pending";
  if (Number.isFinite(dueTs) && dueTs > 0 && dueTs < now) return "Not Taken";
  return "Ongoing";
}

function statusClass(exam) {
  const status = getExamStatus(exam);
  if (status === "Done") return "badge-done";
  if (status === "Terminated") return "badge-terminated";
  if (status === "Not Taken") return "badge-not-taken";
  if (status === "Pending") return "badge-pending";
  if (status === "Ongoing") return "badge-active";
  return "badge-neutral";
}

async function openTakeExam(exam) {
  _warmGazeModel();
  if (getExamStatus(exam) === "Pending") {
    showToastMessage("This exam is not yet open to be taken.");
    return;
  }
  if (getExamStatus(exam) === "Not Taken") {
    showToastMessage("This exam is already closed and can no longer be taken.");
    return;
  }
  if (exam.is_done && !canRetakeExam(exam)) {
    await openResultsModal(exam);
    return;
  }

  // Recheck face position for every exam, including when the camera is already active.
  _stopScreenShare();
  pendingExam = exam;
  _screenDetails = null;
  permissionError.value = "";
  precheckFaceVisible.value = false;
  precheckStatus.value = 'checking';
  showPermissionModal.value = true;
  if (mediaStreamActive.value && activeMediaStream) {
    await nextTick();
    if (permVideoEl.value) permVideoEl.value.srcObject = activeMediaStream;
    _startPrecheckFaceCheck();
  }
}

async function requestMediaPermissions() {
  permissionError.value = "";
  permissionLoading.value = true;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: true,
    });
    activeMediaStream = stream;
    mediaStreamActive.value = true;
    // Show live preview inside the permission modal.
    await nextTick();
    if (permVideoEl.value) {
      permVideoEl.value.srcObject = stream;
    }
    _startPrecheckFaceCheck();
  } catch (err) {
    let msg = "Camera or microphone access was denied.";
    if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
      msg = "No camera or microphone was found on this device.";
    } else if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
      msg = "Permission denied. Please allow camera and microphone access in your browser settings and try again.";
    } else if (err.name === "NotReadableError") {
      msg = "Camera or microphone is already in use by another application.";
    }
    permissionError.value = msg;
    mediaStreamActive.value = false;
  } finally {
    permissionLoading.value = false;
  }
}

function _stopScreenShare() {
  const stream = _screenShareStream;
  _screenShareStream = null;
  screenShareReady.value = false;
  if (stream) {
    stream.getVideoTracks().forEach((track) => { track.onended = null; track.stop(); });
  }
  if (_screenShareVideo) {
    _screenShareVideo.pause();
    _screenShareVideo.srcObject = null;
    _screenShareVideo = null;
  }
}

async function requestScreenShare() {
  if (!navigator.mediaDevices?.getDisplayMedia || screenShareLoading.value) {
    permissionError.value = 'This browser does not support screen sharing. Use a current desktop browser.';
    return;
  }
  permissionError.value = '';
  screenShareLoading.value = true;
  let stream = null;
  try {
    // This must run directly from the student's click. The browser always asks
    // which surface to share; a single tab cannot show other opened tabs.
    stream = await navigator.mediaDevices.getDisplayMedia({
      video: { displaySurface: 'monitor' },
      audio: false,
      monitorTypeSurfaces: 'include',
      surfaceSwitching: 'exclude',
    });
    if (!showPermissionModal.value || !pendingExam) {
      stream.getTracks().forEach((item) => item.stop());
      return;
    }
    const track = stream.getVideoTracks()[0];
    if (track?.getSettings().displaySurface !== 'monitor') {
      stream.getTracks().forEach((item) => item.stop());
      stream = null;
      throw new Error('Select Entire Screen, not a browser tab or window, then try again.');
    }
    _stopScreenShare();
    const video = document.createElement('video');
    video.muted = true;
    video.playsInline = true;
    video.srcObject = stream;
    await video.play();
    _screenShareStream = stream;
    _screenShareVideo = video;
    screenShareReady.value = true;
    track.onended = () => {
      screenShareReady.value = false;
      if (takingExam.value && !examTerminated.value && !submitting.value) {
        void _onScreenShareEnded();
      } else {
        _stopScreenShare();
      }
    };
  } catch (err) {
    stream?.getTracks().forEach((item) => item.stop());
    permissionError.value = err?.message?.startsWith('Select Entire Screen')
      ? err.message
      : 'Screen sharing was cancelled or unavailable. Share your entire screen to start the exam.';
  } finally {
    screenShareLoading.value = false;
  }
}

async function _checkSingleDisplay() {
  if (typeof window.getScreenDetails === 'function') {
    try {
      _screenDetails = await window.getScreenDetails();
    } catch {
      permissionError.value = 'Allow the browser to check connected displays before starting the exam.';
      return false;
    }
  } else if (typeof window.screen?.isExtended !== 'boolean') {
    permissionError.value = 'This browser cannot check connected displays. Use a desktop browser that supports display checks.';
    return false;
  }
  if (hasExtendedDisplay(window.screen, _screenDetails)) {
    permissionError.value = 'An extended monitor is connected. Disconnect it or switch to one display before continuing.';
    return false;
  }
  permissionError.value = '';
  return true;
}

async function proceedFromPermissionModal() {
  if (!mediaStreamActive.value || !screenShareReady.value || !precheckFaceVisible.value || precheckStatus.value !== 'ready') return;
  if (!await _checkSingleDisplay()) return;
  showPermissionModal.value = false;
  // Keep checking face position while identity verification runs.
  fvAttemptsLeft.value = FV_MAX_ATTEMPTS - 1;
  await _runFaceVerification();
}

/**
 * Capture a webcam snapshot and POST it to the face verification endpoint.
 * Shows the FaceVerificationModal with animated feedback throughout.
 */
async function _runFaceVerification() {
  const exam = pendingExam;
  if (!exam) return;

  // Show the modal in 'verifying' state.
  fvStep.value = 'verifying';
  fvErrorMsg.value = '';
  fvShow.value = true;

  try {
    // Grab a frame from whichever video element has pixels.
    const video = permVideoEl.value || examVideoEl.value;
    if (!video || !video.videoWidth) {
      throw new Error('Webcam not ready. Please try again.');
    }

    // Keep verification uploads small and consistent so YuNet can reuse its
    // cached detector input size across devices and retry attempts.
    const canvas = document.createElement('canvas');
    const captureWidth = Math.min(480, video.videoWidth);
    canvas.width = captureWidth;
    canvas.height = Math.round((video.videoHeight / video.videoWidth) * captureWidth);
    const captureCtx = canvas.getContext('2d');
    captureCtx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82));
    if (!blob) throw new Error('Could not capture webcam frame.');

    const form = new FormData();
    form.append('webcam_image', blob, `verify_${Date.now()}.jpg`);

    const { data } = await api.post(
      `/api/student/exams/${exam.id}/verify-face/`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );

    if (data.verified) {
      fvStep.value = 'success';
      // Briefly confirm success, then proceed without making the student wait.
      setTimeout(async () => {
        fvShow.value = false;
        if (!screenShareReady.value || !precheckFaceVisible.value || precheckStatus.value !== 'ready') {
          showPermissionModal.value = true;
          await nextTick();
          if (permVideoEl.value && activeMediaStream) permVideoEl.value.srcObject = activeMediaStream;
          return;
        }
        pendingExam = null;
        await _doOpenExam(exam);
        await nextTick();
        if (examVideoEl.value && activeMediaStream) {
          examVideoEl.value.srcObject = activeMediaStream;
        }
      }, 900);
    } else {
      // Verification failed.
      console.warn('[FV] Verification failed:', data);
      fvErrorMsg.value = data.message || data.error || 'Face did not match the registered photo.';
      fvStep.value = 'failed';
    }
  } catch (err) {
    console.error('[FV] Exception:', err, 'response:', err?.response?.data);
    const status = err?.response?.status;
    if (status === 404) {
      // No face photo registered for this student.
      fvStep.value = 'no-photo';
    } else {
      fvErrorMsg.value =
        err?.response?.data?.error ||
        err?.response?.data?.message ||
        err?.message ||
        'Face verification failed. Please try again.';
      fvStep.value = 'failed';
    }
  }
}


function _onFaceVerifyRetry() {
  if (fvAttemptsLeft.value <= 0) return;
  fvAttemptsLeft.value--;
  _runFaceVerification();
}

function _onFaceVerifyCancel() {
  _stopPrecheckFaceCheck();
  fvShow.value = false;
  pendingExam = null;
  _stopScreenShare();
  // Stop the media stream since the student cancelled.
  if (activeMediaStream && !takingExam.value) {
    activeMediaStream.getTracks().forEach((t) => t.stop());
    activeMediaStream = null;
    mediaStreamActive.value = false;
  }
}

function cancelPermissionModal() {
  _stopPrecheckFaceCheck();
  showPermissionModal.value = false;
  permissionError.value = "";
  pendingExam = null;
  _screenDetails = null;
  _stopScreenShare();
  // Stop stream if it was acquired during the modal.
  if (activeMediaStream && !takingExam.value) {
    activeMediaStream.getTracks().forEach(t => t.stop());
    activeMediaStream = null;
    mediaStreamActive.value = false;
  }
}

function _startPrecheckFaceCheck() {
  if (!pendingExam || !activeMediaStream) return;
  _stopPrecheckFaceCheck();
  precheckFaceVisible.value = false;
  precheckStatus.value = 'checking';
  _precheckReadyStreak = 0;
  _checkPrecheckFace(_precheckRunId);
}

async function _checkPrecheckFace(runId) {
  if (runId !== _precheckRunId || !pendingExam || (!showPermissionModal.value && !fvShow.value)) return;
  const video = permVideoEl.value?.videoWidth ? permVideoEl.value : examVideoEl.value;
  if (!video || video.readyState < 2 || !video.videoWidth) {
    _precheckTimer = setTimeout(() => _checkPrecheckFace(runId), 250);
    return;
  }

  const canvas = document.createElement('canvas');
  canvas.width = Math.min(640, video.videoWidth);
  canvas.height = Math.round(video.videoHeight * canvas.width / video.videoWidth);
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
  if (runId !== _precheckRunId) return;
  if (!blob) {
    precheckStatus.value = 'unavailable';
    precheckFaceVisible.value = false;
    return;
  }
  const form = new FormData();
  form.append('image', blob, 'precheck.jpg');
  _precheckController = new AbortController();
  try {
    const { data } = await api.post(
      `/api/student/exams/${pendingExam.id}/precheck-face/`, form,
      { headers: { 'Content-Type': 'multipart/form-data' }, signal: _precheckController.signal, timeout: 20000 },
    );
    if (runId !== _precheckRunId) return;
    const nextState = nextPrecheckFaceState(_precheckReadyStreak, data);
    _precheckReadyStreak = nextState.readyStreak;
    precheckFaceVisible.value = nextState.faceVisible;
    precheckStatus.value = nextState.status;
    _precheckTimer = setTimeout(() => _checkPrecheckFace(runId), 650);
  } catch (err) {
    if (runId !== _precheckRunId) return;
    _precheckReadyStreak = 0;
    precheckFaceVisible.value = false;
    precheckStatus.value = 'unavailable';
  } finally {
    if (runId === _precheckRunId) _precheckController = null;
  }
}

function _warmGazeModel() {
  // Fire-and-forget: dashboard rendering and camera permission stay responsive
  // while the server loads TensorFlow, TFLite, and MediaPipe in the background.
  api.post('/api/gaze/warmup/').catch(() => {
    // The regular exam socket can still initialize the model as a fallback.
  });
}

function _stopPrecheckFaceCheck() {
  _precheckRunId++;
  clearTimeout(_precheckTimer);
  _precheckController?.abort();
  _precheckController = null;
}

async function _doOpenExam(exam) {
  if (!screenShareReady.value) {
    permissionError.value = 'Share your entire screen to start the exam.';
    showPermissionModal.value = true;
    return;
  }
  if (hasExtendedDisplay(window.screen, _screenDetails)) {
    permissionError.value = 'An extended monitor is connected. Disconnect it or switch to one display before continuing.';
    pendingExam = exam;
    showPermissionModal.value = true;
    await nextTick();
    if (permVideoEl.value && activeMediaStream) permVideoEl.value.srcObject = activeMediaStream;
    return;
  }
  _stopPrecheckFaceCheck();
  takingExam.value = exam;
  takingLoading.value = true;
  examQuestions.value = [];
  studentAnswers.value = {};
  examResult.value = null;
  submitError.value = "";
  currentQuestionIndex.value = 0;
  browserWarningCount.value = 0;
  tabSwitchCount.value = 0;
  gazeViolationCount.value = 0;
  gazeNoFaceCount.value = 0;
  gadgetWarningCount.value = 0;
  _clearGazePending();
  _clearAbsenceAlert();
  terminateReason.value = 'tab';
  proctoringWarning.value = { show: false, type: '', title: '', message: '' };
  examTerminated.value = false;
  _isAway = false;
  _browserTerminationPending = false;
  _extendedDisplayActive = false;
  _screenshotShortcutAt = 0;
  clearTimeout(_leaveCaptureJob?.timer);
  _leaveCaptureJob?.resolve(false);
  _leaveCaptureJob = null;
  _lastShortcutLoggedAt.clear();
  browserWarning.value = { show: false, title: '', message: '' };

  try {
    const qRes = await getWithRetry(`/api/student/exams/${exam.id}/questions/`);
    examQuestions.value = qRes.data.questions || [];
    activeExamRestrictions.value = {
      gaze_above: qRes.data.proctoring_restrictions?.gaze_above ?? true,
      gaze_below: qRes.data.proctoring_restrictions?.gaze_below ?? true,
      gaze_left: qRes.data.proctoring_restrictions?.gaze_left ?? true,
      gaze_right: qRes.data.proctoring_restrictions?.gaze_right ?? true,
      gadgets: qRes.data.proctoring_restrictions?.gadgets ?? true,
    };
    for (const q of examQuestions.value) {
      studentAnswers.value[q.id] = "";
    }
    
    // Timer setup
    if (_examTimer) clearInterval(_examTimer);
    const timeLimitMins = qRes.data.time_limit || 0;
    if (timeLimitMins > 0 && qRes.data.started_at) {
      const startedAt = new Date(qRes.data.started_at).getTime();
      const endTime = startedAt + (timeLimitMins * 60 * 1000);
      
      _examTimer = setInterval(() => {
        if (examTerminated.value || submitting.value || !takingExam.value) {
          clearInterval(_examTimer);
          return;
        }
        const now = Date.now();
        const rem = Math.floor((endTime - now) / 1000);
        if (rem <= 0) {
          examTimeRemaining.value = 0;
          clearInterval(_examTimer);
          _timeUpSubmit();
        } else {
          examTimeRemaining.value = rem;
        }
      }, 1000);
    } else {
      examTimeRemaining.value = null;
    }
  } catch (err) {
    submitError.value = err?.response?.data?.error || "Error loading exam.";
    closeTakeExam();
    return;
  } finally {
    takingLoading.value = false;
  }

  _attachProctoringListeners();

  await nextTick();
  if (examVideoEl.value && activeMediaStream) {
    examVideoEl.value.srcObject = activeMediaStream;
  }
  _startProctoringCaptureTimer();
  _startGazeCheckTimer();
  _startGadgetDetectionTimer();
}

function _attachProctoringListeners() {
  _isAway = false;
  _stopExamWindowMonitor = attachExamWindowMonitor({
    doc: document,
    win: window,
    onLeave: (source) => { void _onLeaveExam(source); },
    onReturn: _onReturnToExam,
    onHidden: () => { /* The shared monitor needs time to paint the destination tab. */ },
  });
  _stopExtendedDisplayMonitor = watchExtendedDisplays({
    win: window,
    details: _screenDetails,
    onChange: _onExtendedDisplayChange,
  });

  _keydownHandler = (e) => _onKeydown(e);
  document.addEventListener('keydown', _keydownHandler);

  _copyHandler = (e) => { e.preventDefault(); _onCheatAttempt('copy'); };
  _cutHandler = (e) => { e.preventDefault(); _onCheatAttempt('cut'); };
  document.addEventListener('copy', _copyHandler);
  document.addEventListener('cut', _cutHandler);

  _contextHandler = (e) => { e.preventDefault(); _onCheatAttempt('rightclick'); };
  document.addEventListener('contextmenu', _contextHandler);

  _resizeHandler = () => _handleSplitScreen();
  window.addEventListener('resize', _resizeHandler);
  _handleSplitScreen();

  _keyupHandler = (e) => {
    if (!takingExam.value || examTerminated.value) return;
    if (e.key === 'PrintScreen') {
      _onCheatAttempt('screenshot');
    }
  };
  document.addEventListener('keyup', _keyupHandler);

  _beforeUnloadHandler = (e) => {
    if (!takingExam.value || examTerminated.value) return;
    e.preventDefault();
    e.returnValue = 'You have an exam in progress. Leaving will count as a tab switch.';
    return e.returnValue;
  };
  window.addEventListener('beforeunload', _beforeUnloadHandler);
}

function closeTakeExam() {
  takingExam.value = null;
  activeExamRestrictions.value = {
    gaze_above: true,
    gaze_below: true,
    gaze_left: true,
    gaze_right: true,
    gadgets: true,
  };
  _stopProctoringCaptureTimer();
  _stopGazeCheckTimer();
  _stopScreenShare();
  // Remove ALL proctoring listeners
  _stopExamWindowMonitor?.();
  _stopExamWindowMonitor = null;
  _stopExtendedDisplayMonitor?.();
  _stopExtendedDisplayMonitor = null;
  if (_keydownHandler)    { document.removeEventListener('keydown',    _keydownHandler); _keydownHandler = null; }
  if (_keyupHandler)      { document.removeEventListener('keyup',      _keyupHandler);   _keyupHandler = null; }
  if (_beforeUnloadHandler) { window.removeEventListener('beforeunload', _beforeUnloadHandler); _beforeUnloadHandler = null; }
  if (_copyHandler)       { document.removeEventListener('copy',       _copyHandler);    _copyHandler = null; }
  if (_cutHandler)        { document.removeEventListener('cut',        _cutHandler);     _cutHandler = null; }
  if (_contextHandler)    { document.removeEventListener('contextmenu',_contextHandler); _contextHandler = null; }
  if (_resizeHandler)     { window.removeEventListener('resize',  _resizeHandler);  _resizeHandler = null; }
  _isAway = false;
  _splitScreenActive = false;
  _browserTerminationPending = false;
  _extendedDisplayActive = false;
  _screenshotShortcutAt = 0;
  clearTimeout(_leaveCaptureJob?.timer);
  _leaveCaptureJob?.resolve(false);
  _leaveCaptureJob = null;
  browserWarning.value = { show: false, title: '', message: '' };
  proctoringWarning.value = { show: false, type: '', title: '', message: '' };
  if (!examTerminated.value) {
    browserWarningCount.value = 0;
    tabSwitchCount.value = 0;
  }
  if (_examTimer) { clearInterval(_examTimer); _examTimer = null; }
  // Stop the media stream when the exam is closed.
  if (activeMediaStream) {
    activeMediaStream.getTracks().forEach(t => t.stop());
    activeMediaStream = null;
    mediaStreamActive.value = false;
  }
  _clearAbsenceAlert();
}

// Computed helper â€” is the window currently in split-screen?
const isSplitScreen = computed(() => {
  return window.innerWidth / window.screen.width <= SPLIT_SCREEN_THRESHOLD;
});

function dismissProctoringWarning() {
  if (proctoringWarning.value.type === 'splitscreen' && isSplitScreen.value) {
    proctoringWarning.value = { ...proctoringWarning.value }; // triggers shake animation
    return;
  }
  proctoringWarning.value.show = false;
}

function dismissBrowserWarning() {
  if (document.hidden || !document.hasFocus()) return;
  if (browserWarning.value.type === 'splitscreen' && isSplitScreen.value) return;
  if (browserWarning.value.type === 'extended_monitor' && _extendedDisplayActive) return;
  browserWarning.value.show = false;
}

function dismissTerminatedScreen() {
  examTerminated.value = false;
  fetchMyExams(); // ensure dashboard shows updated state
}

/**
 * Called when student leaves the exam window (tab switch, alt-tab, etc.)
 * Shows the warning immediately — doesn't wait for return.
 */
async function _onLeaveExam(source) {
  if (_isAway) return;
  if (!takingExam.value || submitting.value || examTerminated.value || _browserTerminationPending) return;
  if (Date.now() - _screenshotShortcutAt < SCREENSHOT_FOCUS_GRACE_MS) return;
  _isAway = true;
  browserWarningCount.value += 1;
  tabSwitchCount.value += 1;
  const count = browserWarningCount.value;
  const examId = takingExam.value.id;
  const eventPromise = _logProctoringEvent('tab_switch', {
    message: 'Student switched away from the exam tab or window',
    source,
    metadata: { count, tab_switch_count: tabSwitchCount.value, screen_capture_requested: screenShareReady.value },
    severity: count >= TAB_SWITCH_LIMIT ? 'critical' : 'warning',
  });
  const captureJob = {
    examId,
    eventPromise,
    started: false,
    timer: null,
    resolve: null,
    promise: null,
  };
  captureJob.promise = new Promise((resolve) => { captureJob.resolve = resolve; });
  _leaveCaptureJob = captureJob;
  // A grab on visibilitychange still contains the old exam frame. Wait for
  // the shared monitor to paint the destination before reading its track.
  captureJob.timer = setTimeout(() => { void _startLeaveCapture(captureJob); }, SCREEN_SWITCH_CAPTURE_DELAY_MS);

  if (count >= TAB_SWITCH_LIMIT) {
    _browserTerminationPending = true;
    browserWarning.value = {
      show: true,
      type: 'tab_change',
      title: `Tab change or minimize detected — Warning ${count} of ${TAB_SWITCH_LIMIT}`,
      message: 'Your exam has been terminated due to too many tab switches or minimizing the screen.',
    };
    // Preserve the linked evidence before final submission closes this attempt.
    await Promise.all([eventPromise, captureJob.promise]);
    await _terminateExam();
    return;
  }

  // Show warning immediately when they leave
  browserWarning.value = {
    show: true,
    type: 'tab_change',
    title: `Tab change or minimize detected — Warning ${count} of ${TAB_SWITCH_LIMIT}`,
    message: `You minimized the screen or switched tabs. This is not allowed. You have ${TAB_SWITCH_LIMIT - count} warning${TAB_SWITCH_LIMIT - count === 1 ? '' : 's'} remaining before your exam is automatically terminated.`,
  };

}

async function _startLeaveCapture(job) {
  if (!job || job.started) return job?.promise;
  job.started = true;
  clearTimeout(job.timer);
  try {
    job.resolve(await _captureBrowserScreen(job.examId, job.eventPromise, 'Switched tabs'));
  } catch (err) {
    console.warn('Screen evidence capture failed:', err);
    job.resolve(false);
  }
  if (_leaveCaptureJob === job) _leaveCaptureJob = null;
  return job.promise;
}

async function _onScreenShareEnded() {
  if (!takingExam.value || examTerminated.value || submitting.value || _browserTerminationPending) return;
  _browserTerminationPending = true;
  terminateReason.value = 'screen_share';
  proctoringWarning.value = {
    show: true,
    type: 'alttab',
    title: 'Screen sharing stopped',
    message: 'The exam cannot continue without entire-screen sharing.',
  };
  await _logProctoringEvent('screen_share_stopped', {
    message: 'Student stopped entire-screen sharing during exam',
    source: 'screen_share',
    severity: 'critical',
  });
  await _terminateExam();
}

/**
 * Called when student returns to the exam window.
 * Keeps the warning visible so they must dismiss it.
 */
function _onReturnToExam(source) {
  if (!_isAway) return;
  _isAway = false;
  if (examTerminated.value) return;
  if (!takingExam.value || submitting.value) return;
  // Warning stays visible â€” student must click "I Understand" to dismiss
}

/**
 * Detect screenshot shortcuts that reach the page and show a warning.
 * OS-level screenshots cannot be reliably blocked or detected by a web page.
 */
function _onKeydown(e) {
  if (!takingExam.value || examTerminated.value) return;

  const ctrl  = e.ctrlKey || e.metaKey;
  const shift = e.shiftKey;
  const key   = e.key;

  // OS Snipping tools often use Win+Shift+S or Mac Cmd+Shift+3/4/5
  const isSnippingTool = ctrl && shift && ['s', '3', '4', '5'].includes(key.toLowerCase());

  // PrintScreen â€” blank the screen briefly as deterrent, show warning
  if (key === 'PrintScreen' || isSnippingTool) {
    e.preventDefault();
    _onCheatAttempt('screenshot');
    return;
  }

  // Block Ctrl+C (copy), Ctrl+X (cut), Ctrl+A (select all), Ctrl+P (print)
  if (ctrl && ['c','x','a','p'].includes(key.toLowerCase()) && !shift) {
    e.preventDefault();
    if (key.toLowerCase() === 'c') _onCheatAttempt('copy');
    if (key.toLowerCase() === 'x') _onCheatAttempt('cut');
    return;
  }

  // Block dev-tools: F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C, Ctrl+U
  if (
    key === 'F12' ||
    (ctrl && shift && ['i','j','c'].includes(key.toLowerCase())) ||
    (ctrl && key.toLowerCase() === 'u')
  ) {
    e.preventDefault();
    return;
  }

  // Block Alt+Tab attempt (Alt key alone)
  if (e.altKey && key === 'Tab') {
    e.preventDefault();
    return;
  }
}

/** Warn and log actions visible to the browser. */
function _onCheatAttempt(reason) {
  if (!takingExam.value || examTerminated.value || submitting.value || _browserTerminationPending) return;
  const now = Date.now();
  if (now - (_lastShortcutLoggedAt.get(reason) || 0) < 1500) return;
  _lastShortcutLoggedAt.set(reason, now);
  const messages = {
    screenshot : 'Taking screenshots during an exam is not allowed.',
    copy       : 'Copying exam content is not allowed during an exam.',
    cut        : 'Cutting exam content is not allowed during an exam.',
    rightclick : 'Right-clicking is disabled during an exam.',
  };
  const titles = {
    screenshot : 'Screenshot attempt detected',
    copy       : 'Action Not Allowed',
    cut        : 'Action Not Allowed',
    rightclick : 'Action Not Allowed',
  };
  if (reason === 'screenshot') {
    _screenshotShortcutAt = now;
    browserWarningCount.value += 1;
    const count = browserWarningCount.value;
    const examId = takingExam.value.id;
    const eventPromise = _logProctoringEvent('screenshot_attempt', {
      message: 'Screenshot shortcut attempted',
      source: 'keyboard',
      metadata: { count },
      severity: count >= TAB_SWITCH_LIMIT ? 'critical' : 'warning',
    });
    const evidencePromise = _captureBrowserScreen(examId, eventPromise, 'Screenshot attempt', false);
    if (count >= TAB_SWITCH_LIMIT) {
      _browserTerminationPending = true;
      terminateReason.value = 'screenshot';
      proctoringWarning.value = {
        show: true, type: 'cheat', title: `Warning ${count} of ${TAB_SWITCH_LIMIT}`,
        message: 'Your exam has been terminated after five browser warnings.',
      };
      void Promise.all([eventPromise, evidencePromise]).then(() => _terminateExam());
    } else {
      proctoringWarning.value = {
        show: true, type: 'cheat', title: `Screenshot attempt — Warning ${count} of ${TAB_SWITCH_LIMIT}`,
        message: `Screenshot attempts are not allowed. ${TAB_SWITCH_LIMIT - count} browser warnings remaining.`,
      };
    }
    return;
  }
  // Show the warning and record other attempted actions in the exam log.
  proctoringWarning.value = {
    show    : true,
    type    : 'cheat',
    title   : titles[reason] || 'Action Not Allowed',
    message : messages[reason] || 'This action is not allowed during an exam.',
  };
  const eventTypes = {
    screenshot: 'screenshot_attempt',
    copy: 'copy_attempt',
    cut: 'cut_attempt',
    rightclick: 'right_click',
  };
  if (eventTypes[reason]) {
    void _logProctoringEvent(eventTypes[reason], {
      message: messages[reason],
      source: reason === 'rightclick' ? 'contextmenu' : 'keyboard',
      severity: 'warning',
    });
  }
}

function _onExtendedDisplayChange(extended) {
  if (!takingExam.value || submitting.value || examTerminated.value || _browserTerminationPending) return;
  if (!extended) {
    _extendedDisplayActive = false;
    if (browserWarning.value.type === 'extended_monitor') browserWarning.value.show = false;
    return;
  }
  if (!_extendedDisplayActive) {
    _extendedDisplayActive = true;
    browserWarningCount.value += 1;
    const count = browserWarningCount.value;
    const eventPromise = _logProctoringEvent('extended_monitor', {
      message: 'Additional display connected during exam',
      source: 'display_check',
      metadata: { count },
      severity: count >= TAB_SWITCH_LIMIT ? 'critical' : 'warning',
    });
    if (count >= TAB_SWITCH_LIMIT) {
      _browserTerminationPending = true;
      terminateReason.value = 'extended_monitor';
      browserWarning.value = {
        show: true, type: 'extended_monitor', title: `Warning ${count} of ${TAB_SWITCH_LIMIT}`,
        message: 'Your exam has been terminated after five browser warnings. An additional display was detected.',
      };
      void eventPromise.then(() => _terminateExam());
      return;
    }
  }
  browserWarning.value = {
    show: true,
    type: 'extended_monitor',
    title: `Extended monitor detected — Warning ${browserWarningCount.value} of ${TAB_SWITCH_LIMIT}`,
    message: 'Additional displays are not allowed during this exam. Disconnect the other display to continue.',
  };
}

function _handleSplitScreen() {
  if (!takingExam.value || submitting.value || _browserTerminationPending) return;
  const ratio = window.innerWidth / window.screen.width;
  if (ratio <= SPLIT_SCREEN_THRESHOLD) {
    if (!_splitScreenActive) {
      _splitScreenActive = true;
      browserWarningCount.value += 1;
      
      if (browserWarningCount.value >= TAB_SWITCH_LIMIT) {
        _browserTerminationPending = true;
        terminateReason.value = 'split_screen';
        browserWarning.value = {
          show: true,
          type: 'splitscreen',
          title: `Warning ${browserWarningCount.value} of ${TAB_SWITCH_LIMIT}`,
          message: 'Your exam has been terminated after too many browser-window violations.',
        };
        const eventPromise = _logProctoringEvent('split_screen', {
          message: 'Student used split-screen or resized the exam window',
          source: 'split_screen',
          metadata: { count: browserWarningCount.value, ratio },
          severity: 'critical',
        });
        void Promise.all([
          eventPromise,
          _captureBrowserScreen(takingExam.value.id, eventPromise, 'Split-screen detected', false),
        ]).then(() => _terminateExam());
        return;
      }

      // Keep window resizing separate from leaving the exam tab.
      const eventPromise = _logProctoringEvent('split_screen', {
        message: 'Split screen or non-maximized window detected',
        source: 'split_screen',
        severity: 'warning',
        metadata: { count: browserWarningCount.value, ratio },
      });
      void _captureBrowserScreen(takingExam.value.id, eventPromise, 'Split-screen detected', false);
      
      // Always show/keep the split-screen warning when in split mode
      browserWarning.value = {
        show: true,
        type: 'splitscreen',
        title: `Warning ${browserWarningCount.value} of ${TAB_SWITCH_LIMIT} (Split Screen Detected)`,
        message: `Split screen is not allowed. You have ${TAB_SWITCH_LIMIT - browserWarningCount.value} warning${TAB_SWITCH_LIMIT - browserWarningCount.value === 1 ? '' : 's'} remaining. Please maximize your browser window to continue.`,
      };
    }
  } else {
    _splitScreenActive = false;
    if (browserWarning.value.type === 'splitscreen' && browserWarning.value.show) {
      // Student maximized — auto-dismiss the split-screen warning
      browserWarning.value.show = false;
    }
  }
}

async function _terminateExam() {
  if (examTerminated.value) return; // guard against double-call
  const terminatedExam = takingExam.value;
  const reason = terminateReason.value;
  const terminatedExamId = terminatedExam?.id;
  const finalTabSwitches = tabSwitchCount.value;
  const finalBrowserWarnings = browserWarningCount.value;
  const finalGazeViolations = gazeViolationCount.value;
  const finalNoFaceCount = gazeNoFaceCount.value;
  await _captureProctoringSnapshot(`Exam auto-terminated (${reason})`, { examId: terminatedExamId });
  examTerminated.value = true; // show root-level terminated screen immediately
  submitting.value = true;
  // Close exam modal right away so student can't keep answering
  closeTakeExam();
  try {
    const payload = {
      answers: Object.keys(studentAnswers.value).map(qId => ({
        question_id: Number(qId),
        answer_text: studentAnswers.value[qId]
      })),
      terminated: true,
      tab_switches: finalTabSwitches,
      browser_warning_count: finalBrowserWarnings,
      gaze_violations: finalGazeViolations,
      gaze_no_face: finalNoFaceCount,
      termination_reason: reason,
    };
    if (terminatedExam) {
      await api.post(`/api/student/exams/${terminatedExam.id}/submit/`, payload, { timeout: 60000 });
    }
    await fetchMyExams();
  } catch (err) {
    // Submission failed but exam is still terminated on the client side
    console.error('Terminated exam submission error:', err);
  } finally {
    submitting.value = false;
  }
}

async function _timeUpSubmit() {
  if (examTerminated.value || submitting.value) return;
  await _recordProctoringStrike('time_up', {
    message: 'Exam time limit reached',
    source: 'timer',
    severity: 'info',
    caption: 'Exam time limit reached',
  });
  proctoringWarning.value = {
    show: true,
    type: 'timeup',
    title: 'Time is Up!',
    message: 'The time allocated for this exam has expired. Your answers have automatically been submitted.'
  };
  await submitExam();
}

async function submitExam() {
  submitError.value = "";
  submitting.value = true;
  // Hard-stop the WebSocket BEFORE posting — prevents any in-flight gaze frame
  // from racing with the submit and causing the backend to see is_done=False
  // during the immediately-following my-answers GET.
  _stopGazeWsLoop();
  const submittedExam = takingExam.value;
  const payload = {
    answers: Object.keys(studentAnswers.value).map(qId => ({
      question_id: Number(qId),
      answer_text: studentAnswers.value[qId]
    })),
    terminated: false,
    tab_switches: tabSwitchCount.value,
    browser_warning_count: browserWarningCount.value,
  };
  _stopGazeCheckTimer();
  try {
    const { data } = await api.post(
      `/api/student/exams/${submittedExam.id}/submit/`,
      payload,
      { timeout: 60000 },
    );
    closeTakeExam();
    await fetchMyExams();
    const updatedExam = exams.value.find(e => e.id === submittedExam.id) || submittedExam;
    await openResultsModal(updatedExam, data);
  } catch (err) {
    submitError.value = err?.response?.data?.error || "Failed to submit exam.";
    if (takingExam.value && !examTerminated.value) {
      _startGazeCheckTimer();
      _startGadgetDetectionTimer();
    }
  } finally {
    submitting.value = false;
  }
}

async function openResultsModal(exam, seed = null) {
  resultsModal.value = exam;
  resultsLoading.value = true;
  // Seed guard: trust the submit response if it has any score data.
  // This covers: auto-graded exams (mc_total > 0), essay-only (mc_total === 0),
  // and terminated exams. We no longer require mc_total != null to avoid
  // the stuck-loading bug when the exam has no auto-graded questions.
  const seedHasData = seed && (
    seed.submitted === true
    || seed.mc_total != null
    || seed.mc_score != null
    || seed.mc_total === 0
    || seed.terminated === true
  );
  if (seedHasData) {
    resultsData.value = {
      submitted: true,
      mc_total: seed.mc_total ?? null,
      mc_correct: seed.mc_correct ?? null,
      mc_score: seed.mc_score ?? null,
      integrity_score: seed.integrity_score ?? null,
      started_at: seed.started_at,
      submitted_at: seed.submitted_at || new Date().toISOString(),
      terminated: seed.terminated,
      tab_switches: seed.tab_switches,
    };
    resultsLoading.value = false;
  } else {
    resultsData.value = {};
  }
  try {
    // Small delay so the DB write from submit() has propagated before we read.
    await new Promise((resolve) => setTimeout(resolve, 300));
    const res = await getWithRetry(`/api/student/exams/${exam.id}/my-answers/`);
    if (res.data?.submitted) {
      resultsData.value = res.data;
    }
  } catch {
    if (!resultsData.value?.mc_total && !seedHasData) {
      resultsData.value = {};
    }
  } finally {
    resultsLoading.value = false;
  }
}

function closeResultsModal() {
  resultsModal.value = null;
  resultsData.value = {};
}

function startRetakeFromResults() {
  const exam = resultsModal.value;
  closeResultsModal();
  if (exam) openTakeExam(exam);
}

function goStudentDashboard() {
  router.push("/student/dashboard");
}

function goSettings() {
  router.push("/student/settings");
}

function goStudentCourses() {
  router.push("/student/courses");
}

function openStudentCourse(courseId) {
  router.push(`/student/courses/${courseId}`);
}

function selectedCourseExamsCount(courseId) {
  return exams.value.filter((exam) => Number(exam.subject_id) === Number(courseId)).length;
}

function subjectBannerClass(index) {
  const variants = ["banner-teal", "banner-gold", "banner-blue", "banner-gray"];
  return variants[index % variants.length];
}

function backToStudentCourses() {
  router.push("/student/courses");
}

function syncStudentCourseFromRoute() {
  const courseId = route.params.courseId;
  selectedSubjectId.value = courseId ? Number(courseId) : null;
}

onMounted(async () => {
  updateTime();
  timeInterval = setInterval(updateTime, 1000);
  _warmGazeModel();
  await Promise.all([fetchMySubjects(), fetchMyExams()]);
  if (examUpdatesStopped) return;
  syncStudentCourseFromRoute();
  connectExamUpdates();
  document.addEventListener('visibilitychange', refreshExamsWhenVisible);
});

onUnmounted(() => {
  stopExamUpdates();
  _stopScreenShare();
  if (activeMediaStream) {
    activeMediaStream.getTracks().forEach(t => t.stop());
    activeMediaStream = null;
  }
  _clearAbsenceAlert();
  // Clean up ALL proctoring listeners
  _stopExamWindowMonitor?.();
  _stopExamWindowMonitor = null;
  _stopExtendedDisplayMonitor?.();
  _stopExtendedDisplayMonitor = null;
  if (_resizeHandler) window.removeEventListener('resize', _resizeHandler);
  if (_keydownHandler) document.removeEventListener('keydown', _keydownHandler);
  if (_keyupHandler) document.removeEventListener('keyup', _keyupHandler);
  if (_beforeUnloadHandler) window.removeEventListener('beforeunload', _beforeUnloadHandler);
  if (_copyHandler) document.removeEventListener('copy', _copyHandler);
  if (_cutHandler) document.removeEventListener('cut', _cutHandler);
  if (_contextHandler) document.removeEventListener('contextmenu', _contextHandler);
  clearInterval(timeInterval);
});

watch(
  () => route.params.courseId,
  () => {
    syncStudentCourseFromRoute();
  },
);

// Wire the floating PiP video whenever the stream becomes active.
watch(mediaStreamActive, async (val) => {
  if (val) {
    await nextTick();
    if (examVideoEl.value && activeMediaStream) {
      examVideoEl.value.srcObject = activeMediaStream;
    }
  }
});

async function performLogout() {
  await signOut(auth);
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  localStorage.removeItem("role");
  router.push("/");
}
</script>


<style scoped>
@import '@/assets/dashboard.css';

/* â”€â”€ Student-specific â”€â”€ */

.absence-toast {
  position: fixed;
  top: 0.75rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10050;
  width: min(520px, calc(100vw - 2rem));
  max-width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin: 0 1rem 1rem;
  padding: 0.85rem 1rem;
  border-radius: 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  box-shadow: 0 8px 24px rgba(220, 38, 38, 0.12);
}
.absence-toast-icon {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-weight: 800;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.absence-toast-text { display: flex; flex-direction: column; gap: 0.15rem; font-size: 0.9rem; line-height: 1.35; }
.absence-toast-text strong { font-weight: 800; }

.face-hold-overlay {
  position: fixed;
  inset: 0;
  z-index: 10040;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
.face-hold-panel {
  max-width: 420px;
  padding: 1.75rem 1.5rem;
  border-radius: 16px;
  background: #fff;
  border: 1px solid #fecaca;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
  text-align: center;
}
.face-hold-panel h2 { margin: 0 0 0.75rem; font-size: 1.25rem; color: #991b1b; }
.face-hold-panel p { margin: 0; color: #475569; line-height: 1.5; font-size: 0.95rem; }

/* Fullscreen exam modal */
.fullscreen-modal {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: #f0f2f5; z-index: 9999;
  display: flex; flex-direction: column; overflow: hidden;
}
.fullscreen-modal.exam-taking-screen {
  background: #bcc5ce;
  color: #1f2937;
  overflow-y: auto;
}
.exam-question-info { background: #d1d8df; }
.exam-question-panel { background: #d3dae1; }
.exam-question-panel textarea {
  background: #e6eaee;
  color: #1f2937;
}

/* Permission modal */
.perm-card { max-width: 480px !important; max-height: calc(100vh - 2rem); overflow-y: auto; padding: 2rem; gap: 1rem; display: flex; flex-direction: column; align-items: center; text-align: center; border-radius: 20px !important; }
.perm-header { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; }
.perm-icon-ring { width: 72px; height: 72px; border-radius: 50%; background: #d1fae5; display: flex; align-items: center; justify-content: center; color: #059669; }
.perm-header h2 { margin: 0; font-size: 1.22rem; color: #0f0f0f; font-weight: 800; }
.perm-header p { margin: 0; font-size: 0.86rem; color: #6b7280; line-height: 1.5; }
.perm-preview-wrap { width: 100%; position: relative; border-radius: 14px; overflow: hidden; background: #0f0f0f; aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; border: 1px solid #e8eaed; }
.perm-video { width: 100%; height: 100%; object-fit: cover; display: block; transform: scaleX(-1); }
.perm-video-placeholder { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; color: rgba(255,255,255,0.4); gap: 0.5rem; font-size: 0.82rem; }
.perm-live-badge { position: absolute; top: 0.6rem; left: 0.6rem; background: rgba(0,0,0,0.65); color: #fff; font-size: 0.7rem; font-weight: 800; letter-spacing: 0.06em; padding: 0.22rem 0.6rem; border-radius: 999px; display: flex; align-items: center; gap: 0.35rem; }
.perm-live-dot { width: 7px; height: 7px; border-radius: 50%; background: #ef4444; display: inline-block; animation: pulseDot 1.2s infinite; }
@keyframes pulseDot { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.35; transform: scale(0.75); } }
.perm-error { color: #dc2626; font-size: 0.84rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 0.6rem 1rem; width: 100%; text-align: left; margin: 0; }
.perm-caution { width: 100%; margin: 0; padding: 0.7rem 0.85rem; border: 1px solid #f4d28a; border-radius: 10px; background: #fffbeb; color: #854d0e; font-size: 0.79rem; line-height: 1.5; text-align: left; }
.perm-face-status { width: 100%; margin: 0; padding: 0.7rem 0.85rem; border-radius: 10px; background: #eff6ff; color: #1e40af; font-size: 0.82rem; font-weight: 600; text-align: left; }
.perm-face-status--ready { background: #ecfdf5; color: #166534; }
.perm-face-status--too_far, .perm-face-status--multiple_faces, .perm-face-status--unavailable { background: #fef2f2; color: #b91c1c; }
.perm-actions { display: flex; flex-wrap: wrap; gap: 0.75rem; width: 100%; justify-content: flex-end; }
.perm-allow-btn { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.4rem; }
.perm-spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Floating PiP */
.cam-pip { position: fixed; top: 1.25rem; right: 1.25rem; z-index: 10000; filter: drop-shadow(0 8px 24px rgba(0,0,0,0.3)); animation: pipIn 0.35s cubic-bezier(0.34,1.56,0.64,1) both; }
@keyframes pipIn { from { opacity: 0; transform: scale(0.7) translateY(-20px); } to { opacity: 1; transform: scale(1) translateY(0); } }
.cam-pip-inner { position: relative; width: 240px; border-radius: 14px; overflow: hidden; background: #0f0f0f; border: 2.5px solid #34d399; aspect-ratio: 4/3; }
.cam-pip-video { width: 100%; height: 100%; object-fit: cover; display: block; transform: scaleX(-1); }
.cam-pip-direction-badge { position: absolute; top: 0.4rem; right: 0.4rem; z-index: 2; color: #fff; font-size: 0.65rem; font-weight: 800; letter-spacing: 0.04em; padding: 0.2rem 0.5rem; border-radius: 999px; white-space: nowrap; text-shadow: 0 1px 3px rgba(0,0,0,0.5); animation: dirBadgePop 0.15s cubic-bezier(0.34,1.56,0.64,1) both; }
@keyframes dirBadgePop { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
.cam-pip-badge { position: absolute; top: 0.5rem; left: 0.5rem; background: rgba(0,0,0,0.65); color: #fff; font-size: 0.68rem; font-weight: 800; letter-spacing: 0.07em; padding: 0.2rem 0.55rem; border-radius: 999px; display: flex; align-items: center; gap: 0.3rem; }
.cam-pip-gaze { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.85)); padding: 0.5rem 0.45rem 0.4rem; font-size: 0.62rem; color: #e5e7eb; line-height: 1.3; }
.cam-pip-gaze-label { display: block; font-weight: 800; color: #5eead4; letter-spacing: 0.04em; text-transform: uppercase; }
.cam-pip-gadget-status { display: block; margin-top: 0.15rem; color: #bfdbfe; font-weight: 700; }
.cam-pip-gadget-unavailable { color: #fca5a5; }
.cam-pip-gaze-stats { display: block; margin-top: 0.15rem; opacity: 0.95; }
.cam-pip-gaze-warn { color: #fcd34d; }
.cam-pip-gaze-pending { color: #93c5fd; font-style: italic; }

/* Live direction alert — sits BELOW the video box as a normal block */
.cam-pip-dir-alert {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  background: rgba(15,15,25,0.88);
  backdrop-filter: blur(6px);
  border-radius: 0 0 10px 10px;
  border: 1px solid rgba(255,255,255,0.10);
  border-top: none;
  padding: 0.24rem 0.5rem 0.24rem 0.45rem;
  font-size: 0.58rem;
  color: #f3f4f6;
  width: 100%;
  box-sizing: border-box;
}
.cam-pip-dir-icon {
  font-size: 0.78rem;
  line-height: 1;
  flex-shrink: 0;
  color: #fbbf24;
}
.cam-pip-dir-body {
  display: flex;
  flex-direction: column;
  gap: 0.14rem;
  flex: 1;
  min-width: 0;
}
.cam-pip-dir-label {
  font-weight: 700;
  font-size: 0.58rem;
  letter-spacing: 0.02em;
  color: #fde68a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cam-pip-dir-bar-track {
  width: 100%;
  height: 3px;
  background: rgba(255,255,255,0.15);
  border-radius: 999px;
  overflow: hidden;
}
.cam-pip-dir-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.1s linear, background 0.3s ease;
}
.cam-pip-dir-timer {
  font-size: 0.55rem;
  color: rgba(255,255,255,0.6);
  font-variant-numeric: tabular-nums;
}

/* Slide-in / slide-out for the direction alert (slides down into view from above) */
.dir-alert-enter-active { transition: all 0.2s cubic-bezier(0.34,1.56,0.64,1); }
.dir-alert-leave-active { transition: all 0.15s ease-in; }
.dir-alert-enter-from, .dir-alert-leave-to { opacity: 0; transform: translateY(-4px) scaleY(0.9); }

/* Toast */

/* Proctoring overlay */
.proctor-overlay { position: fixed; inset: 0; z-index: 10000; background: rgba(0,0,0,0.88); backdrop-filter: blur(12px); display: flex; align-items: center; justify-content: center; animation: proctorFadeIn 0.25s ease; }
.browser-leave-overlay { z-index: 10060; }
@keyframes proctorFadeIn { from { opacity: 0; } to { opacity: 1; } }
.proctor-box { max-width: 480px; width: 90%; background: #fff; border-radius: 24px; padding: 2.5rem 2rem; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 0.9rem; border: 1px solid #e8eaed; box-shadow: 0 32px 80px rgba(0,0,0,0.25); animation: proctorSlideUp 0.3s cubic-bezier(0.175,0.885,0.32,1.275); }
@keyframes proctorSlideUp { from { transform: scale(0.9) translateY(20px); opacity: 0; } to { transform: scale(1) translateY(0); opacity: 1; } }
.proctor-box.alttab { border-color: rgba(245,158,11,0.4); }
.proctor-box.splitscreen { border-color: rgba(59,130,246,0.4); }
.proctor-box.terminated { border-color: rgba(220,38,38,0.4); }
.proctor-box.cheat { border-color: rgba(0,166,153,0.4); }
.proctor-icon { width: 64px; height: 64px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-bottom: 0.25rem; }
.proctor-box.alttab .proctor-icon { background: #fef3c7; color: #d97706; }
.proctor-box.splitscreen .proctor-icon { background: #e6eaf2; color: #1D3461; }
.proctor-box.terminated .proctor-icon { background: #fee2e2; color: #dc2626; }
.proctor-box.cheat .proctor-icon { background: #d1fae5; color: #059669; }
.proctor-box h2 { margin: 0; font-size: 1.3rem; font-weight: 800; color: #0f0f0f; letter-spacing: -0.02em; }
.proctor-box p { margin: 0; font-size: 0.9rem; color: #6b7280; line-height: 1.6; }
.proctor-counter { display: flex; align-items: baseline; gap: 0.4rem; margin: 0.25rem 0; }
.strike-count { font-size: 3rem; font-weight: 900; color: #d97706; line-height: 1; letter-spacing: -0.03em; }
.strike-label { font-size: 1rem; color: #9ca3af; font-weight: 600; }
.proctor-dismiss { margin-top: 0.5rem; padding: 0.75rem 1.75rem; border-radius: 10px; border: 1.5px solid #e8eaed; font-family: inherit; font-size: 0.92rem; font-weight: 700; cursor: pointer; transition: all 0.2s ease; background: #f8f9fa; color: #0f0f0f; }
.proctor-dismiss:hover { background: #0f0f0f; color: #fff; border-color: #0f0f0f; transform: translateY(-1px); }
.proctor-box.terminated .proctor-dismiss { display: none; }
.proctor-dismiss-blocked { background: #fef2f2 !important; border-color: #fecaca !important; color: #dc2626 !important; cursor: not-allowed !important; }
.proctor-dismiss-blocked:hover { transform: none !important; animation: shakeBtn 0.4s ease; }
@keyframes shakeBtn { 0%,100% { transform: translateX(0); } 20% { transform: translateX(-6px); } 40% { transform: translateX(6px); } 60% { transform: translateX(-4px); } 80% { transform: translateX(4px); } }
.no-capture { -webkit-user-select: none; -moz-user-select: none; user-select: none; }
.no-capture * { -webkit-user-select: none; -moz-user-select: none; user-select: none; }
.no-capture input, .no-capture textarea { -webkit-user-select: text; -moz-user-select: text; user-select: text; }
.strike-indicator { display: flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.85rem; border-radius: 8px; font-size: 0.82rem; font-weight: 700; background: #f0f2f5; color: #6b7280; border: 1px solid #e8eaed; transition: all 0.3s ease; }
.strike-indicator.warning { background: #fef3c7; color: #d97706; border-color: rgba(245,158,11,0.3); }
.strike-indicator.danger { background: #fee2e2; color: #dc2626; border-color: rgba(220,38,38,0.3); animation: pulseWarning 1s ease-in-out infinite; }
@keyframes pulseWarning { 0%,100% { opacity: 1; } 50% { opacity: 0.65; } }
.view-results-btn { display: flex; align-items: center; gap: 0.4rem; background: #0f0f0f; color: #fff; border: none; padding: 0.4rem 0.78rem; border-radius: 8px; font-size: 0.78rem; font-weight: 700; cursor: pointer; white-space: nowrap; font-family: inherit; transition: all 0.2s; }
.view-results-btn:hover { background: #00a699; }

/* Results modal */
.results-overlay { position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,0.55); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; padding: 1.5rem; animation: overlayIn 0.2s ease; }
@keyframes overlayIn { from { opacity: 0; } to { opacity: 1; } }
.results-card { background: #fff; border-radius: 24px; width: 100%; max-width: 560px; box-shadow: 0 24px 64px rgba(0,0,0,0.18); overflow: hidden; animation: cardIn 0.3s cubic-bezier(0.175,0.885,0.32,1.275); }
@keyframes cardIn { from { transform: scale(0.94) translateY(16px); opacity: 0; } to { transform: scale(1) translateY(0); opacity: 1; } }
.results-header { display: flex; align-items: center; justify-content: space-between; padding: 1.5rem 1.5rem 1.25rem; border-bottom: 1px solid #f0f0f0; }
.results-header-left { display: flex; align-items: center; gap: 0.85rem; }
.results-icon-wrap { width: 44px; height: 44px; border-radius: 12px; background: #d1fae5; color: #059669; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.results-breadcrumb { margin: 0 0 0.2rem; font-size: 0.75rem; color: #9ca3af; font-weight: 500; }
.results-title { margin: 0; font-size: 1.1rem; font-weight: 800; color: #0f0f0f; letter-spacing: -0.02em; }
.results-close-btn { width: 36px; height: 36px; border-radius: 10px; border: 1.5px solid #e8eaed; background: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #6b7280; transition: all 0.18s; flex-shrink: 0; }
.results-close-btn:hover { background: #f8f9fa; color: #0f0f0f; border-color: #d1d5db; }
.results-score-hero { display: flex; align-items: center; gap: 2rem; padding: 2rem 1.75rem; background: #f8f9fa; border-bottom: 1px solid #f0f0f0; }
.results-score-ring { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.score-ring-svg { width: 120px; height: 120px; }
.score-ring-label { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; flex-direction: row; gap: 1px; }
.score-pct { font-size: 1.9rem; font-weight: 900; color: #0f0f0f; letter-spacing: -0.04em; line-height: 1; }
.score-pct-sign { font-size: 0.85rem; font-weight: 700; color: #6b7280; position: relative; top: -0.4rem; }
.results-score-info { display: flex; flex-direction: column; gap: 0.6rem; }
.score-fraction { display: flex; align-items: baseline; gap: 0.2rem; }
.score-num { font-size: 2rem; font-weight: 900; color: #0f0f0f; letter-spacing: -0.03em; }
.score-denom { font-size: 0.95rem; color: #6b7280; font-weight: 500; }
.score-pending { font-size: 1rem; color: #9ca3af; font-style: italic; }
.score-badge { display: inline-block; padding: 0.3rem 0.85rem; border-radius: 999px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em; width: fit-content; }
.badge-pass { background: #d1fae5; color: #065f46; }
.badge-average { background: #fef3c7; color: #92400e; }
.badge-fail { background: #fee2e2; color: #991b1b; }
.results-details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; padding: 0.5rem 0; }
.results-detail-item { display: flex; flex-direction: column; gap: 0.2rem; padding: 0.85rem 1.5rem; border-bottom: 1px solid #f8f9fa; }
.results-detail-item:nth-child(odd) { border-right: 1px solid #f8f9fa; }
.detail-label { font-size: 0.7rem; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.06em; }
.detail-value { font-size: 0.88rem; font-weight: 600; color: #0f0f0f; }
.detail-done { color: #059669; }
.results-footer { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; border-top: 1px solid #f0f0f0; gap: 1rem; flex-wrap: wrap; }
.results-note { margin: 0; font-size: 0.78rem; color: #9ca3af; }
.results-back-btn { background: #1D3461; color: #fff; border: none; padding: 0.6rem 1.25rem; border-radius: 10px; font-family: inherit; font-size: 0.88rem; font-weight: 600; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
.results-back-btn:hover { background: #162a4f; }

/* Moodle results (legacy) */
.moodle-results-container { width: 100%; max-width: 1000px; margin: 1.5rem auto 4rem; padding: 3rem; background: #fff; border-radius: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); border: 1px solid #e8eaed; }
.hover-underline:hover { text-decoration: underline !important; }
.m-badge-green { background: #d1fae5; color: #065f46; padding: 0.4rem 0.8rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; border: 1px solid rgba(5,150,105,0.2); }
.moodle-attempts-box { background: #fff; border: 1px solid #e8eaed; border-radius: 14px; }
.moodle-attempts-table { width: 100%; border-collapse: collapse; }
.moodle-attempts-table th, .moodle-attempts-table td { padding: 0.85rem 1rem; border-bottom: 1px solid #f0f0f0; text-align: left; font-size: 0.9rem; }
.moodle-attempts-table th { width: 140px; color: #0f0f0f; font-weight: 700; background: #f8f9fa; text-align: right; }
.moodle-review-not-permitted { padding: 1.5rem 1rem; color: #6b7280; font-size: 0.9rem; }
</style>

