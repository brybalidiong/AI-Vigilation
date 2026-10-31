<template>
  <div class="app-wrapper dashboard-role dashboard-role--admin">
    <div class="dashboard-container">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-logo">
          <span class="sidebar-brand-mark" aria-hidden="true"><img src="/branding/ai-vigilation-mark.png" alt="" /></span>
          <span class="sidebar-brand-lockup">
            <span class="sidebar-brand-name">AI-Vigilation</span>
            <span class="sidebar-brand-context">Admin workspace</span>
          </span>
        </div>

        <nav class="sidebar-nav" aria-label="Admin navigation">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="nav-item"
            :class="{ active: activeTab === tab.key }"
            :aria-pressed="activeTab === tab.key"
            @click="selectAdminSection(tab.key)"
            :id="`nav-${tab.key}`"
          >
            <component :is="'svg'" class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="tab.icon"/>
            <span>{{ tab.label }}</span>
            <span v-if="tab.count !== undefined" class="nav-count">{{ tab.count }}</span>
          </button>
        </nav>

        <div class="sidebar-footer-nav">
          <div class="sidebar-user-info">
            <div class="sidebar-user-avatar">A</div>
            <div class="sidebar-user-text">
              <span class="sidebar-user-name">Administrator</span>
              <span class="sidebar-user-role">System admin</span>
            </div>
          </div>
          <button class="nav-item logout-nav" @click="requestLogout" id="logout-btn" title="Logout">
            <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Log Out
          </button>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="main-content" :class="{ 'main-content--dashboard': activeTab === 'overview' }">
        <header class="main-header">
          <div class="header-titles">
            <span class="dashboard-eyebrow">{{ currentDate }}</span>
            <h1 v-if="activeTab === 'overview'">Dashboard</h1>
            <h1 v-if="activeTab === 'courses'">Courses</h1>
            <h1 v-if="activeTab === 'instructors'">Instructors</h1>
            <h1 v-if="activeTab === 'students'">Students</h1>
            <h1 v-if="activeTab === 'ai-model'">Gaze model</h1>
            <p class="header-sub" v-if="activeTab === 'overview'">Exam integrity and campus activity at a glance.</p>
            <p class="header-sub" v-if="activeTab === 'courses'">Create courses, organize them by institute, and assign instructors.</p>
            <p class="header-sub" v-if="activeTab === 'instructors'">Register instructors and manage access without losing their course records.</p>
            <p class="header-sub" v-if="activeTab === 'students'">Manage enrollment and review exam identity photos.</p>
            <p class="header-sub" v-if="activeTab === 'ai-model'">Select the gaze classifier used for every exam.</p>
          </div>
          <div class="header-actions">
            <div class="role-pill">Administrator</div>
          </div>
        </header>
        <div v-if="loadError" class="admin-inline-error" role="alert">
          <span>{{ loadError }}</span>
          <button type="button" @click="fetchInstructors(); fetchStudents()">Retry</button>
        </div>

        <!-- Overview Tab -->
        <section v-if="activeTab === 'overview'" class="admin-overview">
          <div class="dashboard-welcome">
            <div class="dashboard-welcome__copy">
              <span class="dashboard-welcome__eyebrow">Administration overview</span>
              <h2>See how exams are going across campus.</h2>
              <p>Review recorded violations, prohibited devices, and integrity by institute alongside your student and instructor roster.</p>
            </div>
            <button type="button" class="dashboard-welcome__action" @click="pendingFaceCount ? openPendingReviews() : selectAdminSection('students')">
              {{ pendingFaceCount ? `View ${pendingFaceCount} unverified student${pendingFaceCount === 1 ? '' : 's'}` : 'Manage students' }}
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
            </button>
          </div>
          <div class="stats-grid">
            <button type="button" class="stat-card stat-card--link" id="stat-instructors" :aria-label="`View ${activeInstructorCount} active instructors`" @click="selectAdminSection('instructors')">
              <div class="stat-icon instructor-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              </div>
              <div class="stat-body">
                <p class="stat-label">Active Instructors</p>
                <SkeletonLoader v-if="loadingInstructors" type="text" width="4rem" height="2rem" />
                <h2 v-else class="stat-value">{{ activeInstructorCount }}</h2>
              </div>
            </button>
            <button type="button" class="stat-card stat-card--link" id="stat-students" :aria-label="`View ${enrolledStudentCount} enrolled students`" @click="selectAdminSection('students')">
              <div class="stat-icon student-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <div class="stat-body">
                <p class="stat-label">Enrolled Students</p>
                <SkeletonLoader v-if="loadingStudents" type="text" width="4rem" height="2rem" />
                <h2 v-else class="stat-value">{{ enrolledStudentCount }}</h2>
              </div>
            </button>
            <div class="stat-card" id="stat-attempts">
              <div class="stat-icon exam-icon">
                <svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/></svg>
              </div>
              <div class="stat-body"><p class="stat-label">Completed attempts</p><SkeletonLoader v-if="loadingAnalytics && !analytics" type="text" width="4rem" height="2rem" /><h2 v-else class="stat-value">{{ analytics?.summary?.completed_attempts ?? '—' }}</h2></div>
            </div>
            <div class="stat-card" id="stat-integrity">
              <div class="stat-icon integrity-icon">
                <svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 3 3 7v5c0 5 3.7 8.4 9 9 5.3-.6 9-4 9-9V7l-9-4Z"/><path d="m8.5 12 2.3 2.3 4.7-4.7"/></svg>
              </div>
              <div class="stat-body">
                <p class="stat-label">Average integrity</p>
                <SkeletonLoader v-if="loadingAnalytics && !analytics" type="text" width="4rem" height="2rem" />
                <h2 v-else class="stat-value">{{ formatIntegrity(analytics?.summary?.average_integrity) }}</h2>
              </div>
            </div>
          </div>

          <section class="analytics-section" aria-labelledby="analytics-heading">
            <div class="analytics-heading">
              <div>
                <span class="admin-section-kicker">Exam oversight</span>
                <h2 id="analytics-heading">Integrity analytics</h2>
                <p>All recorded exam attempts. Institute averages use completed attempts with integrity reports.</p>
              </div>
              <button type="button" class="analytics-refresh" :disabled="loadingAnalytics" @click="fetchAnalytics">{{ loadingAnalytics ? 'Refreshing…' : 'Refresh data' }}</button>
            </div>
            <div v-if="analyticsError" class="admin-inline-error" role="alert">
              <span>{{ analyticsError }}</span>
              <button type="button" @click="fetchAnalytics">Retry</button>
            </div>
            <div v-if="loadingAnalytics && !analytics" class="analytics-loading" role="status">Loading exam analytics…</div>
            <template v-else-if="analytics">
              <div class="analytics-metrics">
                <div class="analytics-metric"><span>Recorded violations</span><strong>{{ analytics.summary.recorded_violations }}</strong><small>Classified proctoring events</small></div>
                <div class="analytics-metric"><span>Gadget alerts</span><strong>{{ gadgetAlertCount }}</strong><small>{{ formatShare(gadgetAlertCount, analytics.summary.recorded_violations) }} of recorded violations</small></div>
                <div class="analytics-metric"><span>Flagged attempts</span><strong>{{ formatShare(analytics.summary.flagged_attempts, analytics.summary.completed_attempts) }}</strong><small>{{ analytics.summary.flagged_attempts }} of {{ analytics.summary.completed_attempts }} completed attempts</small></div>
                <div class="analytics-metric"><span>Auto-terminated</span><strong>{{ formatShare(analytics.summary.terminated_attempts, analytics.summary.completed_attempts) }}</strong><small>{{ analytics.summary.terminated_attempts }} of {{ analytics.summary.completed_attempts }} completed attempts</small></div>
              </div>
              <div class="analytics-grid">
                <article class="analytics-panel analytics-panel--violations">
                  <div class="analytics-panel__heading"><div><h3>Most recorded violations</h3><p>Share of {{ analytics.summary.recorded_violations }} classified events</p></div><span class="analytics-panel__index">01</span></div>
                  <div v-if="topViolations.length" class="violation-chart">
                    <svg class="violation-chart__plot" viewBox="0 0 680 245" role="img" :aria-label="`Violations by type: ${topViolations.map((item) => `${item.label}, ${item.count} events, ${formatShare(item.count, analytics.summary.recorded_violations)}`).join('; ')}`">
                      <text x="48" y="17" class="violation-chart__axis-title">EVENTS</text>
                      <text x="632" y="17" class="violation-chart__axis-title" text-anchor="end">SHARE</text>
                      <g v-for="tick in violationChartTicks" :key="tick.percent">
                        <line x1="50" :y1="tick.y" x2="630" :y2="tick.y" class="violation-chart__grid" />
                        <text x="42" :y="tick.y + 4" class="violation-chart__axis-label" text-anchor="end">{{ tick.count }}</text>
                        <text x="638" :y="tick.y + 4" class="violation-chart__axis-label">{{ tick.percent }}%</text>
                      </g>
                      <polyline :points="violationChartPoints.map((point) => `${point.x},${point.y}`).join(' ')" class="violation-chart__line" />
                      <g v-for="point in violationChartPoints" :key="point.key">
                        <circle :cx="point.x" :cy="point.y" r="6" class="violation-chart__point" />
                        <text :x="point.x" :y="point.y - 13" class="violation-chart__value" text-anchor="middle">{{ point.count }} · {{ formatShare(point.count, analytics.summary.recorded_violations) }}</text>
                        <text :x="point.x" y="232" class="violation-chart__number" text-anchor="middle">{{ String(point.index + 1).padStart(2, '0') }}</text>
                      </g>
                    </svg>
                    <div class="violation-chart__key" aria-label="Violation types">
                      <div v-for="(item, index) in topViolations" :key="item.key"><span>{{ String(index + 1).padStart(2, '0') }}</span><span class="violation-chart__key-label">{{ item.label }}<small>{{ item.count }} events · {{ formatShare(item.count, analytics.summary.recorded_violations) }}</small></span></div>
                    </div>
                  </div>
                  <p v-else class="analytics-empty">No violations have been recorded yet.</p>
                </article>
                <article class="analytics-panel">
                  <div class="analytics-panel__heading"><div><h3>Prohibited devices</h3><p>Share of recorded device detections</p></div><span class="analytics-panel__index">02</span></div>
                  <div v-if="deviceChartItems.length" class="device-chart">
                    <div class="device-chart__donut" :style="{ background: deviceChartGradient }" role="img" :aria-label="`Device detections by type: ${deviceChartItems.map((item) => `${item.label} ${formatShare(item.count, deviceDetectionCount)}`).join(', ')}`">
                      <div class="device-chart__center"><strong>{{ deviceDetectionCount }}</strong><span>detections</span></div>
                    </div>
                    <div class="device-chart__legend">
                      <div v-for="(device, index) in deviceChartItems" :key="device.label" class="device-chart__item">
                        <span class="device-chart__swatch" :style="{ backgroundColor: deviceChartColors[index] }" aria-hidden="true"></span>
                        <span class="device-chart__label">{{ device.label }}</span>
                        <strong>{{ formatShare(device.count, deviceDetectionCount) }}</strong>
                        <small>{{ device.count }}</small>
                      </div>
                    </div>
                  </div>
                  <p v-else class="analytics-empty">No prohibited devices have been recorded yet.</p>
                </article>
              </div>
              <article class="analytics-panel institute-panel">
                <div class="analytics-panel__heading"><div><h3>Integrity by institute</h3><p>Average score per completed attempt</p></div><span class="analytics-panel__index">03</span></div>
                <div v-if="analytics.lowest_institute" class="institute-insight"><span>Lowest average</span><strong>{{ analytics.lowest_institute.code }} · {{ formatIntegrity(analytics.lowest_institute.average_integrity) }}</strong><small>{{ analytics.lowest_institute.attempts }} {{ analytics.lowest_institute.attempts === 1 ? 'attempt' : 'attempts' }}</small></div>
                <div class="institute-list">
                  <div v-for="item in analytics.institutes" :key="item.code" class="institute-row">
                    <div class="institute-identity"><strong>{{ item.code }}</strong><span>{{ item.name }}</span></div>
                    <div class="institute-measure"><div class="analytics-bar-track"><span :style="{ width: barWidth(item.average_integrity || 0, 100) }"></span></div><small>{{ item.attempts }} {{ item.attempts === 1 ? 'attempt' : 'attempts' }}</small></div>
                    <strong class="institute-score">{{ formatIntegrity(item.average_integrity) }}</strong>
                  </div>
                </div>
              </article>
              <article class="analytics-panel model-integrity-panel">
                <div class="analytics-panel__heading"><div><h3>Integrity by gaze model</h3><p>Average exam integrity for attempts started with each model</p></div><span class="analytics-panel__index">04</span></div>
                <div class="model-integrity-list">
                  <div v-for="model in analytics.gaze_models || []" :key="model.code" class="model-integrity-row">
                    <div class="model-integrity-row__title"><strong>{{ model.name }}</strong><span v-if="model.code === analytics.active_gaze_model">Currently selected</span></div>
                    <div class="model-integrity-row__measure"><div class="analytics-bar-track"><span :style="{ width: barWidth(model.average_integrity || 0, 100) }"></span></div><strong>{{ formatIntegrity(model.average_integrity) }}</strong></div>
                    <small>{{ model.attempts }} {{ model.attempts === 1 ? 'attempt' : 'attempts' }}</small>
                  </div>
                </div>
                <p class="model-integrity-note">Integrity includes all recorded proctoring signals. It is not a measured model accuracy rate. The model is recorded when an attempt begins.</p>
                <p v-if="analytics.unattributed_attempts" class="model-integrity-note">{{ analytics.unattributed_attempts }} earlier {{ analytics.unattributed_attempts === 1 ? 'attempt has' : 'attempts have' }} no recorded model.</p>
              </article>
            </template>
          </section>

          <div class="overview-actions">
            <div class="overview-actions-heading">
              <div>
                <h2>Quick actions</h2>
                <p>Manage people and track student ID verification.</p>
              </div>
            </div>
            <div class="action-grid">
              <button class="action-card" @click="openInstructorForm" id="action-add-instructor">
                <span class="action-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
                </svg></span>
                <span class="action-copy"><strong>Register instructor</strong><small>Add a new instructor account</small></span>
                <span class="action-arrow" aria-hidden="true">→</span>
              </button>
              <button class="action-card" @click="openStudentForm" id="action-enroll-student">
                <span class="action-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                  <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
                </svg></span>
                <span class="action-copy"><strong>Enroll student</strong><small>Create student access</small></span>
                <span class="action-arrow" aria-hidden="true">→</span>
              </button>
              <button class="action-card" @click="openPendingReviews" id="action-review-photos">
                <span class="action-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="12" cy="10" r="3"/><path d="M6 19c.8-2.8 3-4 6-4s5.2 1.2 6 4"/></svg></span>
                <span class="action-copy"><strong>IDs needed <span class="action-count">{{ pendingFaceCount }}</span></strong><small>View students who need to upload an ID</small></span>
                <span class="action-arrow" aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        </section>

        <!-- Courses Tab -->
        <section v-if="activeTab === 'courses'" class="admin-people-page">
          <div class="admin-section-heading">
            <div>
              <span class="admin-section-kicker">Academic catalog</span>
              <h2>Course management</h2>
              <p>Institute courses stay in their own sections. Minor courses are listed separately.</p>
            </div>
          </div>
          <div class="course-tabstrip admin-page-tabs" role="tablist" aria-label="Course management">
            <button type="button" id="course-list-tab" class="course-tab" :class="{ active: !showCreateCourse }" role="tab" :aria-selected="!showCreateCourse" aria-controls="course-list-panel" @click="closeCourseForm">Course catalog <span class="course-tab__count">{{ courses.length }}</span></button>
            <button type="button" id="course-create-tab" class="course-tab" :class="{ active: showCreateCourse }" role="tab" :aria-selected="showCreateCourse" aria-controls="course-create-panel" @click="openCourseForm">Create course</button>
          </div>

          <div v-if="!showCreateCourse" id="course-list-panel" role="tabpanel" aria-labelledby="course-list-tab">
            <div class="admin-filters">
              <label class="admin-filter-field" for="course-search">Search courses
                <input v-model.trim="courseSearch" id="course-search" type="search" class="moodle-search" placeholder="Course name, code, or instructor" />
              </label>
            </div>
            <div v-if="courseLoadError" class="admin-inline-error" role="alert"><span>{{ courseLoadError }}</span><button type="button" @click="fetchCourses">Retry</button></div>
            <div v-if="loadingCourses" class="admin-course-loading" role="status">Loading courses…</div>
            <template v-else>
              <p class="admin-results-count" role="status">Showing {{ filteredCourseCount }} of {{ courses.length }} courses</p>
              <div v-for="group in courseGroups" :key="group.code || 'unclassified'" class="admin-course-group">
                <div class="admin-course-group__heading">
                  <div><span class="admin-section-kicker">{{ group.code === 'MINOR' ? 'Shared curriculum' : group.code || 'Review needed' }}</span><h3>{{ group.name }}</h3></div>
                  <span class="admin-course-group__count">{{ group.courses.length }} {{ group.courses.length === 1 ? 'course' : 'courses' }}</span>
                </div>
                <div v-if="group.courses.length" class="admin-course-list">
                  <article v-for="course in group.courses" :key="course.id" class="admin-course-row">
                    <div class="admin-course-row__identity"><span class="admin-course-code">{{ course.code }}</span><div><h4>{{ course.name }}</h4><p>{{ course.exam_count }} {{ course.exam_count === 1 ? 'exam' : 'exams' }} · {{ course.student_count }} {{ course.student_count === 1 ? 'student' : 'students' }}</p></div></div>
                    <div class="admin-course-row__assignment">
                      <label>Group
                        <select v-model="course._category" class="admin-filter" :disabled="course._saving" :aria-label="`Group for ${course.name}`" @change="onCourseCategoryChange(course)">
                          <option value="" disabled>Choose group</option>
                          <option v-for="category in courseCategories" :key="category.code" :value="category.code">{{ category.code === 'MINOR' ? 'Minor courses' : category.code }}</option>
                        </select>
                      </label>
                      <InstructorAssignmentPicker v-model="course._instructor_ids" :instructors="courseInstructorOptions(course)" :disabled="course._saving || !course._category" :label="course.name" @update:model-value="course._assignment_error = ''" />
                      <div class="admin-course-actions"><span v-if="courseHasPendingChanges(course)" class="admin-course-unsaved">Unsaved changes</span><button type="button" class="row-action admin-course-save" :disabled="course._saving || !courseHasPendingChanges(course)" @click="saveCourseAssignment(course)">{{ course._saving ? 'Saving…' : 'Save' }}</button></div>
                      <p v-if="course._assignment_error || (courseHasPendingChanges(course) && !course._instructor_ids.length)" class="admin-course-assignment-hint" :role="course._assignment_error ? 'alert' : 'status'">{{ course._assignment_error || 'Select at least one instructor before saving.' }}</p>
                    </div>
                  </article>
                </div>
                <p v-else class="admin-course-empty">{{ courseSearch ? 'No matching courses in this group.' : 'No courses in this group yet.' }}</p>
              </div>
            </template>
          </div>

          <form v-else id="course-create-panel" class="create-form-wrapper admin-entry-form" role="tabpanel" aria-labelledby="course-create-tab" @submit.prevent="createCourse">
            <div class="entry-heading"><div><h3 class="form-title">Create a course</h3><p>Choose its institute or Minor courses, then assign one or more active instructors.</p></div></div>
            <div class="inline-form">
              <label class="entry-field" for="course-name">Course name<input id="course-name" v-model.trim="newCourse.name" type="text" maxlength="200" placeholder="e.g. Introduction to Programming" required /></label>
              <label class="entry-field" for="course-code">Course code<input id="course-code" v-model.trim="newCourse.code" type="text" maxlength="50" placeholder="e.g. CS101" required /></label>
              <label class="entry-field" for="course-category">Course group
                <select id="course-category" v-model="newCourse.category" required @change="newCourse.instructor_ids = []">
                  <option value="" disabled>Select institute or minor courses</option>
                  <option v-for="category in courseCategories" :key="category.code" :value="category.code">{{ category.name }}</option>
                </select>
              </label>
            </div>
            <div class="admin-course-create-picker"><InstructorAssignmentPicker v-model="newCourse.instructor_ids" :instructors="assignableInstructors(newCourse.category)" :disabled="!newCourse.category" label="new course" /></div>
            <p v-if="newCourse.category && !assignableInstructors(newCourse.category).length" class="admin-course-hint">There are no active instructors available for this group. Register or restore an instructor first.</p>
            <div class="entry-actions"><button type="button" class="ghost-btn shrink-btn" @click="closeCourseForm">Cancel</button><button type="submit" class="primary-btn shrink-btn" :disabled="courseSaving || !newCourse.instructor_ids.length">{{ courseSaving ? 'Creating…' : 'Create course' }}</button></div>
            <p v-if="courseFormError" class="form-error" role="alert">{{ courseFormError }}</p>
          </form>
        </section>

        <!-- Instructors Tab -->
        <section v-if="activeTab === 'instructors'" class="admin-people-page">
          <div class="admin-section-heading">
            <div>
              <span class="admin-section-kicker">People & access</span>
              <h2>Instructor management</h2>
              <p>Register school accounts, assign institutes, and control access.</p>
            </div>
          </div>
          <div class="course-tabstrip admin-page-tabs" role="tablist" aria-label="Instructor management">
            <button type="button" id="instructor-list-tab" class="course-tab" :class="{ active: !showAddInstructor }" role="tab" :aria-selected="!showAddInstructor" aria-controls="instructor-list-panel" @click="closeInstructorForm">Instructor list <span class="course-tab__count">{{ instructors.length }}</span></button>
            <button type="button" id="add-instructor-btn" class="course-tab" :class="{ active: showAddInstructor }" role="tab" :aria-selected="showAddInstructor" aria-controls="instructor-register-panel" @click="openInstructorForm">Register instructor</button>
          </div>
          <div v-if="!showAddInstructor" id="instructor-list-panel" role="tabpanel" aria-labelledby="instructor-list-tab">
          <div class="moodle-filters admin-filters">
             <label class="admin-filter-field" for="instructor-search">Search instructors
               <input v-model="instructorSearch" type="search" class="moodle-search" placeholder="Name or school email" id="instructor-search"/>
             </label>
             <select v-model="instructorStatusFilter" class="admin-filter" aria-label="Filter instructors">
               <option value="all">All instructors</option>
               <option value="active">Active</option>
               <option value="inactive">Inactive</option>
             </select>
             <select v-model="instructorInstituteFilter" class="admin-filter" aria-label="Filter instructors by institute">
               <option value="all">All institutes</option>
               <option v-for="institute in institutes" :key="institute.code" :value="institute.code">{{ institute.code }} — {{ institute.name }}</option>
               <option value="unassigned">Unassigned</option>
             </select>
             <button v-if="hasInstructorFilters" type="button" class="admin-clear-filters" @click="clearInstructorFilters">Clear filters</button>
          </div>

          <!-- Instructors Table -->
          <p v-if="!loadingInstructors" class="admin-results-count" role="status">Showing {{ filteredInstructors.length }} of {{ instructors.length }} instructors</p>
          <div class="data-table-container">
            <div v-if="loadingInstructors" class="table-skeleton" role="status" aria-label="Loading instructors">
              <SkeletonLoader type="row" v-for="i in 3" :key="i" />
              <span class="visually-hidden">Loading instructors</span>
            </div>
            <table class="data-table" v-else-if="filteredInstructors.length > 0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Institute</th>
                  <th>Status</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="ins in filteredInstructors" :key="ins.id">
                  <td class="bold-td">{{ ins.full_name || '—' }}</td>
                  <td>{{ ins.email }}</td>
                  <td>
                    <select class="admin-filter institute-picker" :value="ins.institute || ''" :disabled="ins._saving" :aria-label="`Institute for ${ins.full_name || ins.email}`" @change="updateInstructorInstitute(ins, $event)">
                      <option value="" disabled>Unassigned</option>
                      <option v-for="institute in institutes" :key="institute.code" :value="institute.code">{{ institute.code }} — {{ institute.name }}</option>
                    </select>
                  </td>
                  <td><span class="status-badge" :class="ins.is_active ? 'badge-done' : 'badge-neutral'">{{ ins.is_active ? 'Active' : 'Inactive' }}</span></td>
                  <td style="text-align: right;">
                    <div class="instructor-row-actions">
                      <button type="button" class="row-action" :disabled="ins._saving" @click="openInstructorEmailEdit(ins)">Edit email</button>
                      <button type="button" class="row-action" :class="ins.is_active ? 'row-action--danger' : 'row-action--restore'" :disabled="ins._saving" @click="setInstructorActive(ins)" :id="`remove-instructor-${ins.id}`">{{ ins._saving ? 'Saving…' : ins.is_active ? 'Deactivate' : 'Restore access' }}</button>
                      <button type="button" class="row-action row-action--danger" :disabled="ins._saving" @click="confirmDeleteInstructor(ins)">Delete</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="admin-empty-state">
              <h3>{{ hasInstructorFilters ? 'No matching instructors' : 'No instructors yet' }}</h3>
              <p>{{ hasInstructorFilters ? 'Try another search or clear the filters.' : 'Register an instructor to grant school account access.' }}</p>
              <button type="button" class="ghost-btn" @click="hasInstructorFilters ? clearInstructorFilters() : openInstructorForm()">{{ hasInstructorFilters ? 'Clear filters' : 'Register instructor' }}</button>
            </div>
          </div>
          </div>
          <form v-else id="instructor-register-panel" class="create-form-wrapper admin-entry-form" role="tabpanel" aria-labelledby="add-instructor-btn" @submit.prevent="registerInstructor">
            <div class="entry-heading"><div><h3 class="form-title">Register instructor</h3><p>Use the instructor's school email. They will sign in with Google.</p></div></div>
            <div class="inline-form">
              <label class="entry-field" for="instructor-first-name">First name<input v-model="newInstructor.first_name" type="text" autocomplete="given-name" id="instructor-first-name"/></label>
              <label class="entry-field" for="instructor-last-name">Last name<input v-model="newInstructor.last_name" type="text" autocomplete="family-name" id="instructor-last-name"/></label>
              <label class="entry-field entry-field--email" for="instructor-email">School email<input v-model="newInstructor.email" type="email" autocomplete="email" :placeholder="`name@${schoolDomain}`" required id="instructor-email"/></label>
              <label class="entry-field entry-field--institute" for="instructor-institute">Institute
                <select v-model="newInstructor.institute" id="instructor-institute" required>
                  <option value="" disabled>Select institute</option>
                  <option v-for="institute in institutes" :key="institute.code" :value="institute.code">{{ institute.code }} — {{ institute.name }}</option>
                </select>
              </label>
            </div>
            <div class="entry-actions">
              <button type="button" class="ghost-btn shrink-btn" @click="closeInstructorForm">Cancel</button>
              <button type="submit" class="primary-btn shrink-btn" :disabled="instructorLoading" id="submit-instructor-btn">{{ instructorLoading ? 'Registering...' : 'Register' }}</button>
            </div>
            <p v-if="instructorError" class="form-error" role="alert">{{ instructorError }}</p>
          </form>
        </section>

        <!-- Students Tab -->
        <section v-if="activeTab === 'students'" class="admin-people-page">
          <div class="admin-section-heading">
            <div>
              <span class="admin-section-kicker">People & access</span>
              <h2>Student management</h2>
              <p>Manage enrollment, institutes, and student ID status.</p>
            </div>
          </div>
          <div class="course-tabstrip admin-page-tabs" role="tablist" aria-label="Student management">
            <button type="button" id="student-list-tab" class="course-tab" :class="{ active: !showAddStudent }" role="tab" :aria-selected="!showAddStudent" aria-controls="student-list-panel" @click="closeStudentForm">Student list <span class="course-tab__count">{{ students.length }}</span></button>
            <button type="button" id="add-student-btn" class="course-tab" :class="{ active: showAddStudent }" role="tab" :aria-selected="showAddStudent" aria-controls="student-register-panel" @click="openStudentForm">Register student</button>
          </div>
          <div v-if="!showAddStudent" id="student-list-panel" role="tabpanel" aria-labelledby="student-list-tab">
          <div class="moodle-filters admin-filters">
             <label class="admin-filter-field" for="student-search">Search students
               <input v-model="studentSearch" type="search" class="moodle-search" placeholder="Name or school email" id="student-search"/>
             </label>
             <select v-model="studentStatusFilter" class="admin-filter" aria-label="Filter students">
               <option value="all">All students</option>
               <option value="enrolled">Enrolled</option>
               <option value="disabled">Access disabled</option>
               <option value="unverified">Student ID needed</option>
             </select>
             <select v-model="studentInstituteFilter" class="admin-filter" aria-label="Filter students by institute">
               <option value="all">All institutes</option>
               <option v-for="institute in institutes" :key="institute.code" :value="institute.code">{{ institute.code }} — {{ institute.name }}</option>
               <option value="unassigned">Unassigned</option>
             </select>
             <button v-if="hasStudentFilters" type="button" class="admin-clear-filters" @click="clearStudentFilters">Clear filters</button>
          </div>

        <!-- Students Table -->
          <p v-if="!loadingStudents" class="admin-results-count" role="status">Showing {{ filteredStudents.length }} of {{ students.length }} students</p>
          <div class="data-table-container">
            <div v-if="loadingStudents" class="table-skeleton" role="status" aria-label="Loading students">
              <SkeletonLoader type="row" v-for="i in 3" :key="i" />
              <span class="visually-hidden">Loading students</span>
            </div>
            <table class="data-table" v-else-if="filteredStudents.length > 0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Institute</th>
                  <th>Status</th>
                  <th style="min-width:200px">Student ID</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="st in filteredStudents" :key="st.id">
                  <td class="bold-td">{{ st.full_name || '—' }}</td>
                  <td>{{ st.email }}</td>
                  <td>
                    <select class="admin-filter institute-picker" :value="st.institute || ''" :disabled="st._saving" :aria-label="`Institute for ${st.full_name || st.email}`" @change="updateStudentInstitute(st, $event)">
                      <option value="" disabled>Unassigned</option>
                      <option v-for="institute in institutes" :key="institute.code" :value="institute.code">{{ institute.code }} — {{ institute.name }}</option>
                    </select>
                  </td>
                  <td>
                    <span class="status-badge" :class="st.is_enrolled ? 'badge-done' : 'badge-neutral'">
                      {{ st.is_enrolled ? 'Enrolled' : 'Access disabled' }}
                    </span>
                  </td>
                  <td style="min-width:240px">
                    <!-- PENDING -->
                    <div v-if="st.face_status === 'pending'" class="face-cell">
                      <div class="face-cell-top">
                        <div class="face-thumb-wrap face-thumb--pending">
                          <img v-if="st.face_pending_photo_url" :src="st.face_pending_photo_url" class="face-thumb-img" alt="Pending" />
                          <span v-else class="face-thumb-placeholder">?</span>
                        </div>
                        <span class="face-label face-label--pending">Pending review</span>
                      </div>
                      <div class="face-btn-row">
                        <button class="face-btn face-btn--approve" @click="reviewStudent = st" :disabled="!!st._faceLoading" :id="`approve-face-${st.id}`">
                          Review photo
                        </button>
                      </div>
                    </div>
                    <!-- APPROVED -->
                    <div v-else-if="st.face_status === 'approved' || (st.face_reupload_allowed && st.face_photo_url)" class="face-cell">
                      <div class="face-cell-top">
                        <div class="face-thumb-wrap face-thumb--approved">
                          <img v-if="st.face_photo_url" :src="st.face_photo_url" class="face-thumb-img" alt="Approved" />
                          <span v-else class="face-thumb-placeholder">✓</span>
                        </div>
                        <span class="face-label face-label--approved">{{ st.face_reupload_allowed ? 'New ID allowed' : 'Verified' }}</span>
                      </div>
                      <label class="face-toggle" :for="`reupload-toggle-${st.id}`">
                        <input
                          type="checkbox"
                          :id="`reupload-toggle-${st.id}`"
                          :checked="st.face_reupload_allowed"
                          :disabled="!!st._faceLoading"
                          @change="toggleReupload(st, $event)"
                        />
                        <span class="face-toggle-slider"></span>
                        <span class="face-toggle-label">Allow new ID</span>
                      </label>
                    </div>
                    <!-- NONE -->
                    <div v-else class="face-cell">
                      <span class="face-label face-label--none">— ID needed</span>
                    </div>
                  </td>
                  <td style="text-align: right;">
                    <div class="instructor-row-actions">
                      <button type="button" class="row-action" :class="st.is_enrolled ? 'row-action--danger' : 'row-action--restore'" :disabled="st._saving" @click="setStudentEnrollment(st)" :id="`remove-student-${st.id}`">{{ st._saving ? 'Saving…' : st.is_enrolled ? 'Disable access' : 'Restore access' }}</button>
                      <button type="button" class="row-action row-action--danger" :disabled="st._saving" @click="confirmDeleteStudent(st)">Delete</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="admin-empty-state">
              <h3>{{ hasStudentFilters ? 'No matching students' : 'No students yet' }}</h3>
              <p>{{ hasStudentFilters ? 'Try another search or clear the filters.' : 'Enroll a student to grant school account access.' }}</p>
              <button type="button" class="ghost-btn" @click="hasStudentFilters ? clearStudentFilters() : openStudentForm()">{{ hasStudentFilters ? 'Clear filters' : 'Enroll student' }}</button>
            </div>
          </div>
          </div>
          <form v-else id="student-register-panel" class="create-form-wrapper admin-entry-form" role="tabpanel" aria-labelledby="add-student-btn" @submit.prevent="enrollStudent">
            <div class="entry-heading"><div><h3 class="form-title">Register student</h3><p>Use the student's school email to allow Google sign-in.</p></div></div>
            <div class="inline-form">
              <label class="entry-field" for="student-first-name">First name<input v-model="newStudent.first_name" type="text" autocomplete="given-name" id="student-first-name" required/></label>
              <label class="entry-field" for="student-last-name">Last name<input v-model="newStudent.last_name" type="text" autocomplete="family-name" id="student-last-name" required/></label>
              <label class="entry-field entry-field--email" for="student-email">School email<input v-model="newStudent.email" type="email" autocomplete="email" :placeholder="`name@${schoolDomain}`" required id="student-email"/></label>
              <label class="entry-field entry-field--institute" for="student-institute">Institute
                <select v-model="newStudent.institute" id="student-institute" required>
                  <option value="" disabled>Select institute</option>
                  <option v-for="institute in institutes" :key="institute.code" :value="institute.code">{{ institute.code }} — {{ institute.name }}</option>
                </select>
              </label>
            </div>
            <div class="entry-actions">
              <button type="button" class="ghost-btn shrink-btn" @click="closeStudentForm">Cancel</button>
              <button type="submit" class="primary-btn shrink-btn" :disabled="studentLoading" id="submit-student-btn">{{ studentLoading ? 'Enrolling...' : 'Register' }}</button>
            </div>
            <p v-if="studentError" class="form-error" role="alert">{{ studentError }}</p>
          </form>
        </section>
        <section v-if="activeTab === 'ai-model'" class="admin-people-page">
          <div class="admin-section-heading"><div>
            <span class="admin-section-kicker">System settings</span>
            <h2>Gaze detection model</h2>
            <p>One model serves all student exams. EfficientNet is recommended while the other exports are being prepared.</p>
          </div></div>
          <div class="gaze-model-panel">
            <p v-if="loadingGazeModels">Checking available models…</p>
            <p v-else-if="gazeModelError" class="form-error" role="alert">{{ gazeModelError }} <button type="button" class="row-action" @click="fetchGazeModels">Retry</button></p>
            <template v-else>
              <p class="gaze-model-current">Currently used: <strong>{{ gazeModels.find(model => model.code === selectedGazeModel)?.name || 'EfficientNet' }}</strong></p>
              <div class="gaze-model-options">
                <label v-for="model in gazeModels" :key="model.code" class="gaze-model-option" :class="{ 'gaze-model-option--selected': pendingGazeModel === model.code, 'gaze-model-option--disabled': !model.installed }">
                  <input v-model="pendingGazeModel" type="radio" name="gaze-model" :value="model.code" :disabled="!model.installed || savingGazeModel" />
                  <span class="gaze-model-option__copy"><strong>{{ model.name }}</strong><small>{{ model.installed ? (model.code === selectedGazeModel ? 'Active' : 'Ready to select') : 'Model file not installed' }}</small></span>
                  <span v-if="model.recommended" class="gaze-model-recommended">Recommended</span>
                </label>
              </div>
              <div class="entry-actions"><button type="button" class="primary-btn shrink-btn" :disabled="savingGazeModel || pendingGazeModel === selectedGazeModel" @click="saveGazeModel">{{ savingGazeModel ? 'Applying…' : 'Apply model' }}</button></div>
              <p class="gaze-model-note">New models must be exported as compatible TFLite files and installed on the backend before they can be selected.</p>
            </template>
          </div>
        </section>
      </main>

      <!-- Confirm Dialog -->
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
      <div v-if="editingInstructor" class="review-backdrop" @click.self="closeInstructorEmailEdit">
        <form class="review-dialog instructor-email-dialog" role="dialog" aria-modal="true" aria-labelledby="instructor-email-title" @submit.prevent="saveInstructorEmail" @keydown.esc="closeInstructorEmailEdit">
          <div class="review-heading">
            <div><p class="review-eyebrow">INSTRUCTOR ACCOUNT</p><h2 id="instructor-email-title">Edit email</h2><p>{{ editingInstructor.full_name || editingInstructor.email }}</p></div>
            <button type="button" class="entry-close" aria-label="Close email editor" :disabled="emailEditSaving" @click="closeInstructorEmailEdit">×</button>
          </div>
          <label class="entry-field" for="edit-instructor-email">School email
            <input id="edit-instructor-email" v-model.trim="editedInstructorEmail" type="email" autocomplete="email" :placeholder="`name@${schoolDomain}`" required :disabled="emailEditSaving" />
          </label>
          <p class="instructor-email-help">The instructor will use this email for their next Google sign-in.</p>
          <p v-if="emailEditError" class="form-error" role="alert">{{ emailEditError }}</p>
          <div class="review-actions">
            <button type="button" class="ghost-btn" :disabled="emailEditSaving" @click="closeInstructorEmailEdit">Cancel</button>
            <button type="submit" class="primary-btn" :disabled="emailEditSaving || !editedInstructorEmail.trim() || editedInstructorEmail.trim().toLowerCase() === editingInstructor.email.toLowerCase()">{{ emailEditSaving ? 'Saving…' : 'Save email' }}</button>
          </div>
        </form>
      </div>
      <div v-if="reviewStudent" class="review-backdrop" @click.self="reviewStudent = null">
        <section class="review-dialog" role="dialog" aria-modal="true" aria-labelledby="review-title" @keydown.esc="reviewStudent = null">
          <div class="review-heading">
            <div><p class="review-eyebrow">IDENTITY REVIEW</p><h2 id="review-title">{{ reviewStudent.full_name || reviewStudent.email }}</h2><p>{{ reviewStudent.email }}</p></div>
            <button type="button" class="entry-close" aria-label="Close review" @click="reviewStudent = null">×</button>
          </div>
          <div class="review-photo">
            <img v-if="reviewStudent.face_pending_photo_url" :src="reviewStudent.face_pending_photo_url" :alt="`Pending ID photo for ${reviewStudent.full_name || reviewStudent.email}`" />
            <p v-else>Photo preview is unavailable. Ask the student to upload it again.</p>
          </div>
          <p class="review-guidance">Check that one face is clear and the photo belongs to this student before approving.</p>
          <div class="review-actions">
            <button type="button" class="ghost-btn" @click="reviewStudent = null">Cancel</button>
            <button type="button" class="row-action row-action--danger" :disabled="!!reviewStudent._faceLoading" @click="confirmRejectFace(reviewStudent)">Reject photo</button>
            <button type="button" class="primary-btn" :disabled="!!reviewStudent._faceLoading || !reviewStudent.face_pending_photo_url" @click="approveFace(reviewStudent)">{{ reviewStudent._faceLoading ? 'Saving…' : 'Approve photo' }}</button>
          </div>
        </section>
      </div>
      <NoticeModal :model-value="Boolean(actionSuccess)" :title="actionSuccessTitle" :message="actionSuccess" @close="actionSuccess = ''" />
      <NoticeModal :model-value="Boolean(actionError)" type="error" title="Action failed" :message="actionError" @close="actionError = ''" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import ConfirmModal from "@/components/ConfirmModal.vue";
import NoticeModal from "@/components/NoticeModal.vue";
import InstructorAssignmentPicker from "@/components/InstructorAssignmentPicker.vue";
import SkeletonLoader from "@/components/SkeletonLoader.vue";

const router = useRouter();
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
const schoolDomain = import.meta.env.VITE_SCHOOL_DOMAIN || "dnsc.edu.ph";
const institutes = [
  { code: 'IC', name: 'Institute of Computing' },
  { code: 'ITED', name: 'Institute of Teachers Education' },
  { code: 'IASS', name: 'Institute of Acquatic and Applied Sciences' },
  { code: 'ILEGG', name: 'Institute of Leadership, Entrepreneurship and Good Governance' },
];
const courseCategories = [...institutes, { code: 'MINOR', name: 'Minor courses' }];

const activeTab = ref("overview");
const currentDate = new Intl.DateTimeFormat('en-PH', {
  weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
}).format(new Date());

const tabs = computed(() => [
  {
    key: "overview",
    label: "Dashboard",
    icon: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
  },
  {
    key: "courses",
    label: "Courses",
    count: coursesLoaded.value ? courses.value.length : undefined,
    icon: '<path d="M4 5.5C6.5 4 9 4 12 5.5c3-1.5 5.5-1.5 8 0V19c-2.5-1.5-5-1.5-8 0-3-1.5-5.5-1.5-8 0z"/><path d="M12 5.5V19"/>',
  },
  {
    key: "instructors",
    label: "Instructors",
    count: instructors.value.length,
    icon: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  },
  {
    key: "students",
    label: "Students",
    count: students.value.length,
    icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  },
  {
    key: 'ai-model', label: 'Gaze model',
    icon: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v3m0 12v3M3 12h3m12 0h3"/>',
  },
]);
const gazeModels = ref([]);
const selectedGazeModel = ref('efficientnet');
const pendingGazeModel = ref('efficientnet');
const loadingGazeModels = ref(true);
const savingGazeModel = ref(false);
const gazeModelError = ref('');

// Instructors
const instructors = ref([]);
const loadingInstructors = ref(true);
const showAddInstructor = ref(false);
const instructorLoading = ref(false);
const instructorError = ref("");
const instructorSearch = ref("");
const instructorStatusFilter = ref('all');
const instructorInstituteFilter = ref('all');
const editingInstructor = ref(null);
const editedInstructorEmail = ref('');
const emailEditError = ref('');
const emailEditSaving = ref(false);
const hasInstructorFilters = computed(() => Boolean(instructorSearch.value) || instructorStatusFilter.value !== 'all' || instructorInstituteFilter.value !== 'all');
const newInstructor = ref({ email: "", first_name: "", last_name: "", institute: "" });

// Courses
const courses = ref([]);
const loadingCourses = ref(true);
const courseLoadError = ref('');
const courseSearch = ref('');
const showCreateCourse = ref(false);
const courseSaving = ref(false);
const courseFormError = ref('');
const newCourse = ref({ name: '', code: '', category: '', instructor_ids: [] });
const filteredCourses = computed(() => {
  const query = courseSearch.value.trim().toLowerCase();
  return courses.value.filter((course) => !query || [
    course.name, course.code, ...(course.instructor_names || []),
  ].some((value) => String(value || '').toLowerCase().includes(query)));
});
const filteredCourseCount = computed(() => filteredCourses.value.length);
const courseGroups = computed(() => {
  const groups = courseCategories.map((category) => ({
    ...category,
    courses: filteredCourses.value.filter((course) => course.category === category.code),
  }));
  const unclassified = filteredCourses.value.filter((course) => !course.category);
  if (unclassified.length) groups.push({ code: '', name: 'Needs institute assignment', courses: unclassified });
  return groups;
});
function assignableInstructors(category) {
  return instructors.value.filter((instructor) => instructor.is_active &&
    (category === 'MINOR' || instructor.institute === category));
}
function courseInstructorOptions(course) {
  return instructors.value.filter((instructor) =>
    (instructor.is_active && (course._category === 'MINOR' || instructor.institute === course._category))
    || course._instructor_ids.includes(instructor.id)
    || course.instructor_ids.includes(instructor.id));
}
function sameInstructorIds(a, b) {
  return a.length === b.length && a.every((id) => b.includes(id));
}
function courseHasPendingChanges(course) {
  return course._category !== course.category || !sameInstructorIds(course._instructor_ids, course.instructor_ids);
}

// Students
const students = ref([]);
const loadingStudents = ref(true);
const showAddStudent = ref(false);
const studentLoading = ref(false);
const studentError = ref("");
const actionSuccess = ref("");
const actionSuccessTitle = ref("");
const actionError = ref("");
const loadError = ref("");
const analytics = ref(null);
const loadingAnalytics = ref(false);
const analyticsError = ref('');
const topViolations = computed(() => (analytics.value?.violations || []).filter((item) => item.count > 0).slice(0, 6));
const violationChartScale = computed(() => {
  const total = analytics.value?.summary?.recorded_violations || 0;
  const highestShare = total ? topViolations.value[0]?.count / total * 100 || 0 : 0;
  return Math.max(10, Math.ceil(highestShare / 10) * 10);
});
const violationChartTicks = computed(() => Array.from({ length: 5 }, (_, index) => {
  const percent = Math.round(violationChartScale.value * (4 - index) / 4);
  return {
    percent,
    count: Math.round((analytics.value?.summary?.recorded_violations || 0) * percent / 100),
    y: 49 + index * 38.75,
  };
}));
const violationChartPoints = computed(() => {
  const total = analytics.value?.summary?.recorded_violations || 0;
  return topViolations.value.map((item, index) => ({
    ...item, index,
    x: topViolations.value.length === 1 ? 340 : 50 + index * 580 / (topViolations.value.length - 1),
    y: 204 - (total ? item.count / total * 100 / violationChartScale.value * 155 : 0),
  }));
});
const gadgetAlertCount = computed(() => analytics.value?.violations?.find((item) => item.key === 'gadget_detected')?.count ?? 0);
const deviceChartColors = ['#1d3461', '#4974ad', '#4b9a96', '#c89550', '#a5b2c4'];
const deviceDetectionCount = computed(() => (analytics.value?.devices || []).reduce((total, item) => total + item.count, 0));
const deviceChartItems = computed(() => {
  const devices = (analytics.value?.devices || []).filter((item) => item.count > 0);
  if (devices.length <= 5) return devices;
  return [...devices.slice(0, 4), {
    label: 'Other devices', count: devices.slice(4).reduce((total, item) => total + item.count, 0),
  }];
});
const deviceChartGradient = computed(() => {
  let start = 0;
  const slices = deviceChartItems.value.map((item, index) => {
    const end = start + item.count / deviceDetectionCount.value * 100;
    const slice = `${deviceChartColors[index]} ${start}% ${end}%`;
    start = end;
    return slice;
  });
  return `conic-gradient(${slices.join(', ')})`;
});
const formatIntegrity = (value) => value === null || value === undefined ? '—' : `${Number(value).toFixed(1)}%`;
const formatShare = (count, total) => total > 0 ? `${(count / total * 100).toFixed(1)}%` : '—';
const barWidth = (value, maximum) => `${maximum ? Math.max(0, Math.min(100, value / maximum * 100)) : 0}%`;
const reviewStudent = ref(null);
const studentStatusFilter = ref('all');
const studentInstituteFilter = ref('all');
const hasStudentFilters = computed(() => Boolean(studentSearch.value) || studentStatusFilter.value !== 'all' || studentInstituteFilter.value !== 'all');
const pendingFaceCount = computed(() => students.value.filter((student) => student.face_status !== 'approved').length);
const activeInstructorCount = computed(() => instructors.value.filter((instructor) => instructor.is_active).length);
const enrolledStudentCount = computed(() => students.value.filter((student) => student.is_enrolled).length);
function showActionSuccess(title, text) {
  actionError.value = '';
  actionSuccessTitle.value = title;
  actionSuccess.value = text;
}
function showActionError(text) {
  actionSuccess.value = '';
  actionError.value = text;
}
const studentSearch = ref("");
const newStudent = ref({ email: "", first_name: "", last_name: "", institute: "" });

function selectAdminSection(section) {
  activeTab.value = section;
  if (section === 'courses' && !coursesLoaded.value) fetchCourses();
  if (section === 'ai-model' && !gazeModelsLoaded) fetchGazeModels();
  if (section === 'courses') closeCourseForm();
  if (section === 'instructors') closeInstructorForm();
  if (section === 'students') closeStudentForm();
}

function openCourseForm() {
  activeTab.value = 'courses';
  if (!coursesLoaded.value) fetchCourses();
  showCreateCourse.value = true;
  courseFormError.value = '';
  nextTick(() => document.getElementById('course-name')?.focus());
}

function closeCourseForm() {
  showCreateCourse.value = false;
  newCourse.value = { name: '', code: '', category: '', instructor_ids: [] };
  courseFormError.value = '';
}

function onCourseCategoryChange(course) {
  const allowed = new Set(assignableInstructors(course._category).map((instructor) => instructor.id));
  course._instructor_ids = course._instructor_ids.filter((id) => allowed.has(id));
  course._assignment_error = '';
}

function openInstructorForm() {
  activeTab.value = 'instructors';
  showAddInstructor.value = true;
  instructorError.value = '';
  nextTick(() => document.getElementById('instructor-email')?.focus());
}

function closeInstructorForm() {
  showAddInstructor.value = false;
  clearInstructorForm();
}

function openStudentForm() {
  activeTab.value = 'students';
  studentStatusFilter.value = 'all';
  showAddStudent.value = true;
  studentError.value = '';
  nextTick(() => document.getElementById('student-email')?.focus());
}

function clearInstructorFilters() {
  instructorSearch.value = '';
  instructorStatusFilter.value = 'all';
  instructorInstituteFilter.value = 'all';
}

function clearStudentFilters() {
  studentSearch.value = '';
  studentStatusFilter.value = 'all';
  studentInstituteFilter.value = 'all';
}

function closeStudentForm() {
  showAddStudent.value = false;
  clearStudentForm();
}

function openPendingReviews() {
  activeTab.value = 'students';
  closeStudentForm();
  studentStatusFilter.value = 'unverified';
  studentInstituteFilter.value = 'all';
  studentSearch.value = '';
}

function confirmRejectFace(student) {
  reviewStudent.value = null;
  openConfirm({
    title: 'Reject face photo?',
    message: `${student.full_name || student.email} will need to upload another photo for identity verification.`,
    confirmText: 'Reject photo',
    onConfirm: () => rejectFace(student),
  });
}

const confirmOpen = ref(false);
const confirmTitle = ref("");
const confirmMessage = ref("");
const confirmVariant = ref("danger");
const confirmConfirmText = ref("Confirm");
const confirmCancelText = ref("Cancel");
let _pendingConfirmCallback = null;

function openConfirm(options) {
  confirmTitle.value = options.title || "Confirm";
  confirmMessage.value = options.message || "Are you sure?";
  confirmVariant.value = options.variant || "danger";
  confirmConfirmText.value = options.confirmText || "Confirm";
  confirmCancelText.value = options.cancelText || "Cancel";
  _pendingConfirmCallback = options.onConfirm || null;
  confirmOpen.value = true;
}

function onConfirmDialog() {
  if (_pendingConfirmCallback) _pendingConfirmCallback();
  clearPendingConfirm();
}

function clearPendingConfirm() {
  _pendingConfirmCallback = null;
  confirmOpen.value = false;
}

function getHeaders() {
  const token = localStorage.getItem("access_token");
  return { Authorization: `Bearer ${token}` };
}

async function fetchInstructors() {
  loadingInstructors.value = true;
  loadError.value = '';
  try {
    const res = await axios.get(`${backendBaseUrl}/api/admin/instructors/`, { headers: getHeaders() });
    instructors.value = res.data.instructors || [];
  } catch (e) {
    loadError.value = e?.response?.data?.error || 'Could not load instructors.';
  } finally {
    loadingInstructors.value = false;
  }
}

async function fetchStudents() {
  loadingStudents.value = true;
  loadError.value = '';
  try {
    const res = await axios.get(`${backendBaseUrl}/api/admin/students/`, { headers: getHeaders() });
    students.value = res.data.students || [];
  } catch (e) {
    loadError.value = e?.response?.data?.error || 'Could not load students.';
  } finally {
    loadingStudents.value = false;
  }
}

const coursesLoaded = ref(false);
async function fetchCourses() {
  loadingCourses.value = true;
  courseLoadError.value = '';
  try {
    const { data } = await axios.get(`${backendBaseUrl}/api/admin/courses/`, { headers: getHeaders() });
    courses.value = (data.courses || []).map((course) => ({
        ...course, _category: course.category, _instructor_ids: [...course.instructor_ids],
    }));
    coursesLoaded.value = true;
  } catch (e) {
    courseLoadError.value = e?.response?.data?.error || 'Could not load courses.';
  } finally {
    loadingCourses.value = false;
  }
}

async function createCourse() {
  courseFormError.value = '';
  courseSaving.value = true;
  try {
    const { data } = await axios.post(`${backendBaseUrl}/api/admin/courses/`, {
      ...newCourse.value, code: newCourse.value.code.trim().toUpperCase(),
    }, { headers: getHeaders() });
    courses.value.push({ ...data, _category: data.category, _instructor_ids: [...data.instructor_ids] });
    closeCourseForm();
    showActionSuccess('Course created', `${data.code} was assigned to ${data.instructor_names.join(', ')}.`);
  } catch (e) {
    courseFormError.value = e?.response?.data?.error || 'Could not create course.';
  } finally {
    courseSaving.value = false;
  }
}

async function saveCourseAssignment(course) {
  if (course._saving || !courseHasPendingChanges(course)) return;
  if (!course._category || !course._instructor_ids.length) {
    course._assignment_error = !course._category ? 'Choose a course group before saving.' : 'Select at least one instructor before saving.';
    return;
  }
  course._assignment_error = '';
  course._saving = true;
  try {
    const { data } = await axios.patch(`${backendBaseUrl}/api/admin/courses/${course.id}/`, {
      category: course._category, instructor_ids: course._instructor_ids,
    }, { headers: getHeaders() });
    Object.assign(course, data, { _category: data.category, _instructor_ids: [...data.instructor_ids] });
    showActionSuccess('Course assignment saved', `${data.code} is assigned to ${data.instructor_names.join(', ')}.`);
  } catch (e) {
    showActionError(e?.response?.data?.error || 'Could not update the course assignment.');
  } finally {
    course._saving = false;
  }
}

async function fetchAnalytics() {
  loadingAnalytics.value = true;
  analyticsError.value = '';
  try {
    const { data } = await axios.get(`${backendBaseUrl}/api/admin/analytics/`, { headers: getHeaders() });
    analytics.value = data;
  } catch (e) {
    analyticsError.value = e?.response?.data?.error || 'Could not load exam analytics.';
  } finally {
    loadingAnalytics.value = false;
  }
}

let gazeModelsLoaded = false;
async function fetchGazeModels() {
  loadingGazeModels.value = true;
  gazeModelError.value = '';
  try {
    const { data } = await axios.get(`${backendBaseUrl}/api/admin/gaze-model/`, { headers: getHeaders() });
    gazeModels.value = data.models || [];
    selectedGazeModel.value = data.selected_model;
    pendingGazeModel.value = data.selected_model;
    gazeModelsLoaded = true;
  } catch (error) {
    gazeModelError.value = error?.response?.data?.error || 'Could not load gaze models.';
  } finally {
    loadingGazeModels.value = false;
  }
}

async function saveGazeModel() {
  savingGazeModel.value = true;
  try {
    const { data } = await axios.patch(`${backendBaseUrl}/api/admin/gaze-model/`, { model_code: pendingGazeModel.value }, { headers: getHeaders() });
    gazeModels.value = data.models || [];
    selectedGazeModel.value = data.selected_model;
    pendingGazeModel.value = data.selected_model;
    showActionSuccess('Gaze model updated', 'The selected gaze model will be used for all exams.');
  } catch (error) {
    pendingGazeModel.value = selectedGazeModel.value;
    showActionError(error?.response?.data?.error || 'Could not switch gaze models.');
  } finally {
    savingGazeModel.value = false;
  }
}

async function registerInstructor() {
  instructorError.value = "";
  newInstructor.value.email = newInstructor.value.email.trim().toLowerCase();
  if (!newInstructor.value.email.endsWith(`@${schoolDomain}`)) {
    instructorError.value = `Use a @${schoolDomain} email address.`;
    return;
  }
  instructorLoading.value = true;
  try {
    const res = await axios.post(`${backendBaseUrl}/api/admin/instructors/`, newInstructor.value, { headers: getHeaders() });
    showActionSuccess('Instructor registered', `Instructor ${res.data.email} was registered.`);
    instructors.value.unshift(res.data);
    instructorInstituteFilter.value = res.data.institute;
    clearInstructorForm();
    showAddInstructor.value = false;
  } catch (e) {
    instructorError.value = e?.response?.data?.error || "Failed to register instructor.";
  } finally {
    instructorLoading.value = false;
  }
}

function setInstructorActive(ins) {
  if (!ins.is_active) {
    updateInstructorActive(ins, true);
    return;
  }
  openConfirm({
    title: "Deactivate instructor?",
    message: `${ins.full_name || ins.email} will no longer be able to sign in. Their courses, exams, and records will be kept.`,
    confirmText: 'Deactivate',
    onConfirm: () => updateInstructorActive(ins, false),
  });
}

async function updateInstructorActive(ins, active) {
  ins._saving = true;
  try {
    const { data } = await axios.patch(`${backendBaseUrl}/api/admin/instructors/${ins.id}/`, { is_active: active }, { headers: getHeaders() });
    ins.is_active = data.is_active;
    showActionSuccess(active ? 'Instructor access restored' : 'Instructor access deactivated', active ? 'Instructor access restored.' : 'Instructor access deactivated.');
  } catch (e) {
    showActionError(e?.response?.data?.error || 'Could not update instructor access.');
  } finally {
    ins._saving = false;
  }
}

function openInstructorEmailEdit(ins) {
  editingInstructor.value = ins;
  editedInstructorEmail.value = ins.email;
  emailEditError.value = '';
  nextTick(() => document.getElementById('edit-instructor-email')?.focus());
}

function closeInstructorEmailEdit() {
  if (emailEditSaving.value) return;
  editingInstructor.value = null;
  editedInstructorEmail.value = '';
  emailEditError.value = '';
}

async function saveInstructorEmail() {
  const ins = editingInstructor.value;
  if (!ins) return;
  const email = editedInstructorEmail.value.trim().toLowerCase();
  if (!email.endsWith(`@${schoolDomain}`)) {
    emailEditError.value = `Use a @${schoolDomain} email address.`;
    return;
  }
  emailEditSaving.value = true;
  try {
    const { data } = await axios.patch(`${backendBaseUrl}/api/admin/instructors/${ins.id}/`, { action: 'set_email', email }, { headers: getHeaders() });
    ins.email = data.email;
    ins.username = data.username;
    editingInstructor.value = null;
    showActionSuccess('Instructor email updated', `${ins.full_name || data.email} can now sign in with ${data.email}.`);
  } catch (e) {
    emailEditError.value = e?.response?.data?.error || 'Could not update instructor email.';
  } finally {
    emailEditSaving.value = false;
  }
}

function confirmDeleteInstructor(ins) {
  openConfirm({
    title: 'Delete instructor account?',
    message: `${ins.full_name || ins.email} will be removed permanently. Reassign all of their courses first to keep courses, exams, and student records.`,
    confirmText: 'Delete instructor',
    onConfirm: () => deleteInstructor(ins),
  });
}

async function deleteInstructor(ins) {
  ins._saving = true;
  try {
    await axios.delete(`${backendBaseUrl}/api/admin/instructors/${ins.id}/`, { headers: getHeaders() });
    instructors.value = instructors.value.filter((item) => item.id !== ins.id);
    showActionSuccess('Instructor deleted', `${ins.full_name || ins.email} was removed.`);
  } catch (e) {
    showActionError(e?.response?.data?.error || 'Could not delete instructor.');
  } finally {
    ins._saving = false;
  }
}

async function updateInstructorInstitute(ins, event) {
  const institute = event.target.value;
  ins._saving = true;
  try {
    const { data } = await axios.patch(`${backendBaseUrl}/api/admin/instructors/${ins.id}/`, { action: 'set_institute', institute }, { headers: getHeaders() });
    ins.institute = data.institute;
    showActionSuccess('Institute updated', `${ins.full_name || ins.email} is now assigned to ${institute}.`);
  } catch (e) {
    event.target.value = ins.institute || '';
    showActionError(e?.response?.data?.error || 'Could not update instructor institute.');
  } finally {
    ins._saving = false;
  }
}

async function enrollStudent() {
  studentError.value = "";
  newStudent.value.email = newStudent.value.email.trim().toLowerCase();
  if (!newStudent.value.email.endsWith(`@${schoolDomain}`)) {
    studentError.value = `Use a @${schoolDomain} email address.`;
    return;
  }
  studentLoading.value = true;
  try {
    const res = await axios.post(`${backendBaseUrl}/api/admin/students/`, newStudent.value, { headers: getHeaders() });
    showActionSuccess(res.data.created ? 'Student enrolled' : 'Student enrollment updated', res.data.created ? `Student ${res.data.email} was enrolled.` : `Student ${res.data.email} enrollment was updated.`);
    const existing = students.value.find((s) => s.id === res.data.id);
    if (existing) Object.assign(existing, res.data);
    else students.value.unshift(res.data);
    studentInstituteFilter.value = res.data.institute;
    clearStudentForm();
    showAddStudent.value = false;
  } catch (e) {
    studentError.value = e?.response?.data?.error || "Failed to enroll student.";
  } finally {
    studentLoading.value = false;
  }
}

function setStudentEnrollment(st) {
  if (!st.is_enrolled) {
    updateStudentEnrollment(st, true);
    return;
  }
  openConfirm({
    title: "Disable student access?",
    message: `${st.full_name || st.email} will not be able to sign in. Their exam records will be kept.`,
    confirmText: 'Disable access',
    onConfirm: () => updateStudentEnrollment(st, false),
  });
}

function confirmDeleteStudent(st) {
  openConfirm({
    title: 'Delete student account?',
    message: `${st.full_name || st.email} will lose access and be removed from student lists and course rosters. Past exam submissions and integrity evidence will remain available for review.`,
    confirmText: 'Delete student',
    onConfirm: () => deleteStudent(st),
  });
}

async function deleteStudent(st) {
  st._saving = true;
  try {
    await axios.delete(`${backendBaseUrl}/api/admin/students/${st.id}/`, { headers: getHeaders() });
    students.value = students.value.filter((item) => item.id !== st.id);
    if (reviewStudent.value?.id === st.id) reviewStudent.value = null;
    showActionSuccess('Student deleted', `${st.full_name || st.email} was removed.`);
  } catch (e) {
    showActionError(e?.response?.data?.error || 'Could not delete student.');
  } finally {
    st._saving = false;
  }
}

async function updateStudentEnrollment(st, enrolled) {
  st._saving = true;
  try {
    const { data } = await axios.patch(`${backendBaseUrl}/api/admin/students/${st.id}/`, { action: 'set_enrollment', is_enrolled: enrolled }, { headers: getHeaders() });
    st.is_enrolled = data.is_enrolled;
    showActionSuccess(enrolled ? 'Student access restored' : 'Student access disabled', enrolled ? 'Student access restored.' : 'Student access disabled.');
  } catch (e) {
    showActionError(e?.response?.data?.error || 'Could not update student access.');
  } finally {
    st._saving = false;
  }
}

async function updateStudentInstitute(st, event) {
  const institute = event.target.value;
  st._saving = true;
  try {
    const { data } = await axios.patch(`${backendBaseUrl}/api/admin/students/${st.id}/`, { action: 'set_institute', institute }, { headers: getHeaders() });
    st.institute = data.institute;
    showActionSuccess('Institute updated', `${st.full_name || st.email} is now assigned to ${institute}.`);
  } catch (e) {
    event.target.value = st.institute || '';
    showActionError(e?.response?.data?.error || 'Could not update student institute.');
  } finally {
    st._saving = false;
  }
}

async function approveFace(st) {
  st._faceLoading = 'approve';
  try {
    const res = await axios.patch(
      `${backendBaseUrl}/api/admin/students/${st.id}/`,
      { action: 'approve_face' },
      { headers: getHeaders() }
    );
    st.face_status = res.data.face_status;
    if (res.data.face_photo_url) st.face_photo_url = res.data.face_photo_url;
    st.face_pending_photo_url = null;
    st.face_reupload_allowed = false;
    reviewStudent.value = null;
    showActionSuccess('Face photo approved', 'The student’s face photo was approved.');
  } catch (e) {
    showActionError(e?.response?.data?.error || 'Could not approve face photo.');
  } finally {
    st._faceLoading = null;
  }
}

async function rejectFace(st) {
  st._faceLoading = 'reject';
  try {
    const res = await axios.patch(
      `${backendBaseUrl}/api/admin/students/${st.id}/`,
      { action: 'reject_face' },
      { headers: getHeaders() }
    );
    st.face_status = res.data.face_status;
    st.face_pending_photo_url = null;
    reviewStudent.value = null;
    showActionSuccess('Face photo rejected', 'The student can submit another face photo.');
  } catch (e) {
    showActionError(e?.response?.data?.error || 'Could not reject face photo.');
  } finally {
    st._faceLoading = null;
  }
}

async function toggleReupload(st, event) {
  st._faceLoading = 'toggle';
  try {
    const res = await axios.patch(
      `${backendBaseUrl}/api/admin/students/${st.id}/`,
      { action: 'toggle_reupload' },
      { headers: getHeaders() }
    );
    st.face_reupload_allowed = res.data.face_reupload_allowed;
    st.face_status = res.data.face_status;
    showActionSuccess(
      res.data.face_reupload_allowed ? 'Photo re-upload enabled' : 'Photo re-upload disabled',
      res.data.face_reupload_allowed
        ? 'Face photo re-upload enabled.'
        : 'Face photo re-upload disabled.'
    );
  } catch (e) {
    event.target.checked = st.face_reupload_allowed;
    showActionError(e?.response?.data?.error || 'Could not change photo upload permission.');
  } finally {
    st._faceLoading = null;
  }
}

function clearInstructorForm() {
  newInstructor.value = { email: "", first_name: "", last_name: "", institute: "" };
  instructorError.value = "";
}

function clearStudentForm() {
  newStudent.value = { email: "", first_name: "", last_name: "", institute: "" };
  studentError.value = "";
}

const filteredInstructors = computed(() => {
  const q = instructorSearch.value.trim().toLowerCase();
  return instructors.value.filter((instructor) => {
    if (instructorStatusFilter.value === 'active' && !instructor.is_active) return false;
    if (instructorStatusFilter.value === 'inactive' && instructor.is_active) return false;
    if (instructorInstituteFilter.value === 'unassigned' && instructor.institute) return false;
    if (instructorInstituteFilter.value !== 'all' && instructorInstituteFilter.value !== 'unassigned' && instructor.institute !== instructorInstituteFilter.value) return false;
    return !q || (instructor.full_name || '').toLowerCase().includes(q)
      || instructor.email.toLowerCase().includes(q);
  }).sort((a, b) => a.email.localeCompare(b.email));
});

const filteredStudents = computed(() => {
  const q = studentSearch.value.trim().toLowerCase();
  return students.value.filter((student) => {
    if (studentStatusFilter.value === 'unverified' && student.face_status === 'approved') return false;
    if (studentStatusFilter.value === 'enrolled' && !student.is_enrolled) return false;
    if (studentStatusFilter.value === 'disabled' && student.is_enrolled) return false;
    if (studentInstituteFilter.value === 'unassigned' && student.institute) return false;
    if (studentInstituteFilter.value !== 'all' && studentInstituteFilter.value !== 'unassigned' && student.institute !== studentInstituteFilter.value) return false;
    return !q || (student.full_name || '').toLowerCase().includes(q)
      || student.email.toLowerCase().includes(q);
  }).sort((a, b) => a.email.localeCompare(b.email));
});

function requestLogout() {
  openConfirm({
    variant: 'neutral',
    title: 'Log out?',
    message: 'You will be signed out of the admin panel and returned to the admin login page.',
    confirmText: 'Log out',
    onConfirm: logout,
  });
}

function logout() {
  localStorage.clear();
  router.push("/admin/login");
}

onMounted(() => {
  fetchInstructors();
  fetchStudents();
  fetchAnalytics();
});
</script>

<style scoped>
@import '@/assets/dashboard.css';

/* Admin specific additions */
.dashboard-role--admin {
  --dash-accent: #1d3461;
  --dash-accent-strong: #162a50;
  --dash-accent-soft: #e8eef8;
  --dash-accent-rgb: 29, 52, 97;
}
.admin-overview,
.admin-people-page,
.admin-inline-error {
  width: 100%;
  max-width: 1420px;
  margin-left: auto;
  margin-right: auto;
}
.admin-overview { display: grid; gap: 1.1rem; }
.analytics-section { display: grid; gap: 1rem; }
.analytics-heading { display: flex; align-items: end; justify-content: space-between; gap: 1rem; padding: .4rem .1rem 0; }
.analytics-heading h2 { margin: .15rem 0; color: #172b4a; font: 750 1.45rem 'Poppins', sans-serif; letter-spacing: -.035em; }
.analytics-heading p { margin: 0; color: #68778d; font-size: .84rem; }
.analytics-refresh { flex: none; border: 1px solid #cbd7e6; border-radius: 9px; background: #fff; color: #1d3461; padding: .65rem .9rem; font: 700 .78rem 'Poppins', sans-serif; cursor: pointer; }
.analytics-refresh:hover:not(:disabled) { background: #f4f7fb; }
.analytics-refresh:disabled { opacity: .55; cursor: wait; }
.analytics-refresh:focus-visible { outline: 3px solid #9db4d8; outline-offset: 2px; }
.analytics-loading { padding: 3rem; border-radius: 16px; background: #fff; color: #63738b; text-align: center; }
.analytics-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .8rem; }
.analytics-metric { display: grid; gap: .2rem; padding: 1.05rem 1.2rem; border: 1px solid #dfe6ef; border-radius: 15px; background: #fff; box-shadow: 0 7px 22px rgba(15, 23, 42, .04); }
.analytics-metric span { color: #617187; font-size: .75rem; font-weight: 700; }
.analytics-metric strong { color: #1b3157; font: 750 1.7rem 'Poppins', sans-serif; letter-spacing: -.045em; line-height: 1.2; }
.analytics-metric small { color: #8a98aa; font-size: .69rem; }
.analytics-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 1rem; }
.analytics-panel { min-width: 0; padding: 1.35rem 1.5rem; border: 1px solid #dfe6ef; border-radius: 18px; background: #fff; box-shadow: 0 10px 30px rgba(15, 23, 42, .045); }
.analytics-panel__heading { display: flex; align-items: start; justify-content: space-between; gap: 1rem; margin-bottom: 1.35rem; }
.analytics-panel__heading h3 { margin: 0 0 .15rem; color: #192b48; font: 750 1rem 'Poppins', sans-serif; }
.analytics-panel__heading p { margin: 0; color: #77869a; font-size: .76rem; }
.analytics-panel__index { color: #a3afbf; font: 700 .72rem 'Poppins', sans-serif; }
.violation-chart { display: grid; gap: .7rem; }
.violation-chart__plot { display: block; width: 100%; height: auto; overflow: visible; }
.violation-chart__grid { stroke: #e7edf5; stroke-width: 1; }
.violation-chart__axis-title { fill: #8998ad; font: 700 10px 'Poppins', sans-serif; letter-spacing: .08em; }
.violation-chart__axis-label { fill: #8b99ac; font: 11px 'Poppins', sans-serif; }
.violation-chart__line { fill: none; stroke: #38649d; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.violation-chart__point { fill: #fff; stroke: #254e86; stroke-width: 3; }
.violation-chart__value { fill: #1d3461; font: 700 11px 'Poppins', sans-serif; }
.violation-chart__number { fill: #71829a; font: 700 11px 'Poppins', sans-serif; }
.violation-chart__key { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .4rem 1rem; padding-top: .7rem; border-top: 1px solid #edf0f5; }
.violation-chart__key div { display: flex; gap: .5rem; min-width: 0; color: #445774; font-size: .72rem; }
.violation-chart__key span { color: #8a9bb1; font-weight: 800; }
.violation-chart__key .violation-chart__key-label { display: grid; color: #445774; font-weight: 600; }
.violation-chart__key-label small { color: #8392a7; font-size: .68rem; font-weight: 400; }
.analytics-bar-track { width: 100%; height: 7px; overflow: hidden; border-radius: 999px; background: #edf1f6; }
.analytics-bar-track span { display: block; height: 100%; border-radius: inherit; background: #6f88ac; }
.analytics-empty { margin: 0; padding: 2rem .5rem; color: #8492a6; font-size: .84rem; text-align: center; }
.device-chart { display: flex; align-items: center; gap: 1.5rem; }
.device-chart__donut { display: grid; place-items: center; flex: none; width: clamp(130px, 15vw, 180px); aspect-ratio: 1; border-radius: 50%; }
.device-chart__center { display: grid; place-content: center; width: 62%; aspect-ratio: 1; border-radius: 50%; background: #fff; text-align: center; }
.device-chart__center strong { color: #1b3157; font: 750 1.6rem 'Poppins', sans-serif; line-height: 1.2; }
.device-chart__center span { color: #75849a; font-size: .68rem; }
.device-chart__legend { display: grid; flex: 1; min-width: 0; }
.device-chart__item { display: grid; grid-template-columns: .65rem minmax(0, 1fr) auto auto; align-items: center; gap: .55rem; padding: .55rem 0; border-bottom: 1px solid #edf0f5; color: #374a64; font-size: .76rem; }
.device-chart__item:last-child { border-bottom: 0; }
.device-chart__swatch { width: .65rem; height: .65rem; border-radius: 50%; }
.device-chart__label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.device-chart__item strong { color: #1d3461; font-size: .78rem; }
.device-chart__item small { min-width: 1.3rem; color: #8492a6; font-size: .7rem; text-align: right; }
.institute-panel { display: grid; gap: .2rem; }
.institute-insight { display: flex; align-items: center; flex-wrap: wrap; gap: .35rem .7rem; padding: .85rem 1rem; margin-bottom: .65rem; border-radius: 10px; background: #f3f6fa; color: #62738c; font-size: .76rem; }
.institute-insight strong { color: #1d3461; font-size: .85rem; }
.institute-insight small { margin-left: auto; font-size: .72rem; }
.institute-list { display: grid; }
.institute-row { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(90px, 1fr) 4.4rem; align-items: center; gap: 1rem; padding: .75rem 0; border-top: 1px solid #edf0f5; }
.institute-identity { display: flex; align-items: baseline; gap: .65rem; min-width: 0; }
.institute-identity strong { flex: none; color: #1b3157; font-size: .8rem; }
.institute-identity span { overflow: hidden; color: #75849a; font-size: .73rem; text-overflow: ellipsis; white-space: nowrap; }
.institute-measure { display: grid; gap: .25rem; }
.institute-measure small { color: #8b98a9; font-size: .67rem; }
.institute-score { color: #1d3461; font-size: .85rem; text-align: right; }
.model-integrity-list { display: grid; }
.model-integrity-row { display: grid; gap: .45rem; padding: .85rem 0; border-top: 1px solid #edf0f5; }
.model-integrity-row__title, .model-integrity-row__measure { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.model-integrity-row__title strong { color: #1b3157; font-size: .83rem; }
.model-integrity-row__title span { color: #527099; font-size: .7rem; font-weight: 700; }
.model-integrity-row__measure .analytics-bar-track { flex: 1; }
.model-integrity-row__measure strong { min-width: 3.8rem; color: #1d3461; font-size: .85rem; text-align: right; }
.model-integrity-row small, .model-integrity-note { margin: 0; color: #8492a6; font-size: .72rem; }
.model-integrity-note { padding-top: .5rem; }
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}
.stat-card {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: .9rem;
  padding: 1.25rem;
  border: 1px solid #dfe6ef;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 10px 30px rgba(15, 23, 42, .055);
  text-align: left;
  font: inherit;
}
.stat-body { min-width: 0; }
.stat-card--link { cursor: pointer; transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease; }
.stat-card--link:hover { border-color: #adbfdb; transform: translateY(-2px); box-shadow: 0 14px 32px rgba(15, 23, 42, .09); }
.stat-card--link:focus-visible { outline: 3px solid rgba(29, 52, 97, .3); outline-offset: 2px; }
.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.instructor-icon { background: #e8f1ff; color: #2458d6; }
.student-icon { background: #e8f5ee; color: #15803d; }
.exam-icon { background: #eef0fa; color: #465b9e; }
.integrity-icon { background: #eaf4f1; color: #187967; }
.stat-label {
  font-size: 0.75rem; color: var(--text-secondary); margin: 0 0 0.25rem;
  font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
}
.stat-value {
  font-family: 'Poppins', sans-serif;
  font-size: 2rem; font-weight: 800; color: var(--text-primary);
  margin: 0; letter-spacing: -0.04em; line-height: 1;
}
.nav-count { margin-left: auto; padding: .12rem .48rem; border-radius: 999px; background: rgba(255,255,255,.12); color: #e7f0ff; font-size: .7rem; font-weight: 700; }
.overview-actions {
  padding: 1.7rem;
  border: 1px solid #e1e7ef;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 10px 30px rgba(15, 23, 42, .055);
}
.overview-actions-heading { margin-bottom: 1.25rem; }
.overview-actions-heading h2 {
  margin: 0 0 .2rem;
  color: #192b48;
  font-family: 'Poppins', sans-serif;
  font-size: 1.25rem;
  font-weight: 750;
  letter-spacing: -.025em;
}
.overview-actions-heading p { margin: 0; color: #64748b; font-size: .85rem; }
.action-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; }
.action-card {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: .8rem;
  padding: 1rem;
  border: 1px solid #e1e7ef;
  border-radius: 14px;
  background: #f8fafd;
  color: #233650;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background .18s ease, border-color .18s ease, transform .18s ease;
}
.action-card:hover { background: #f0f5fc; border-color: #b9cde7; transform: translateY(-2px); }
.action-card:focus-visible { outline: 3px solid #5b8cde; outline-offset: 2px; }
.action-icon { display: grid; place-items: center; flex: 0 0 42px; height: 42px; border-radius: 12px; background: #e7effb; color: #2658a1; }
.action-copy { display: grid; min-width: 0; gap: .2rem; }
.action-copy strong { font-size: .88rem; font-weight: 750; }
.action-copy small { color: #6a7b93; font-size: .73rem; }
.action-arrow { margin-left: auto; color: #6b83a5; font-size: 1.25rem; line-height: 1; }
.action-count { display: inline-flex; min-width: 1.25rem; height: 1.25rem; justify-content: center; align-items: center; margin-left: .25rem; border-radius: 999px; background: #fff0df; color: #9a3412; font-size: .7rem; }
.admin-section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1.25rem;
  margin-bottom: 1.1rem;
}
.admin-section-kicker { color: #58739a; font-size: .69rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.admin-section-heading h2 { margin: .25rem 0; color: #172b4a; font-family: 'Poppins', sans-serif; font-size: 1.4rem; letter-spacing: -.025em; }
.admin-section-heading p { margin: 0; color: #68778d; font-size: .85rem; }
.admin-page-tabs { margin-bottom: 1.25rem; overflow: hidden; border: 1px solid #e1e8f1; border-radius: 14px; }
.admin-page-tabs .course-tab { min-height: 52px; }
.admin-results-count { margin: .25rem 0 .65rem; color: #68778d; font-size: .78rem; font-weight: 650; }
.admin-course-loading { padding: 2rem; border: 1px solid #dfe6ef; border-radius: 15px; background: #fff; color: #68778d; text-align: center; }
.admin-course-group { margin: 1rem 0 1.35rem; padding: 1.2rem; border: 1px solid #dfe6ef; border-radius: 17px; background: #fff; box-shadow: 0 8px 24px rgba(15, 23, 42, .04); }
.admin-course-group__heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0 .15rem 1rem; }
.admin-course-group__heading h3 { margin: .18rem 0 0; color: #172b4a; font: 750 1.05rem 'Poppins', sans-serif; }
.admin-course-group__count { color: #64748b; font-size: .77rem; font-weight: 700; white-space: nowrap; }
.admin-course-list { display: grid; gap: .65rem; }
.admin-course-row { display: grid; grid-template-columns: minmax(190px, 1fr) minmax(380px, 1.6fr); align-items: center; gap: 1.25rem; padding: .95rem 1rem; border: 1px solid #e5eaf2; border-radius: 12px; background: #f9fafc; }
.admin-course-row__identity { display: flex; align-items: center; gap: .85rem; min-width: 0; }
.admin-course-code { flex: none; padding: .38rem .55rem; border-radius: 7px; background: #e9eff7; color: #1d3461; font-size: .7rem; font-weight: 800; letter-spacing: .03em; }
.admin-course-row__identity h4 { overflow: hidden; margin: 0; color: #203553; font-size: .86rem; text-overflow: ellipsis; white-space: nowrap; }
.admin-course-row__identity p { margin: .15rem 0 0; color: #7b899d; font-size: .72rem; }
.admin-course-row__assignment { display: grid; grid-template-columns: minmax(115px, .75fr) minmax(175px, 1.3fr) auto; align-items: end; gap: .55rem; }
.admin-course-row__assignment label { display: grid; gap: .25rem; min-width: 0; color: #6a788d; font-size: .68rem; font-weight: 700; }
.admin-course-row__assignment .admin-filter { width: 100%; min-width: 0; font-size: .75rem; }
.admin-course-actions { display: grid; justify-items: end; gap: .22rem; }
.admin-course-unsaved { color: #8b6330; font-size: .65rem; font-weight: 700; white-space: nowrap; }
.admin-course-assignment-hint { grid-column: 1 / -1; margin: 0; color: #a04428; font-size: .7rem; font-weight: 600; }
.admin-course-create-picker { max-width: 28rem; margin-top: .85rem; }
.admin-course-save { min-height: 41px; padding: .55rem .8rem; color: #1d3461; }
.admin-course-save:disabled { opacity: .48; cursor: default; }
.admin-course-empty { margin: 0; padding: 1rem .25rem .35rem; color: #8390a2; font-size: .8rem; }
.admin-course-hint { margin: 1rem 0 0; color: #916524; font-size: .78rem; }
.admin-empty-state { display: grid; justify-items: center; gap: .55rem; padding: 3.5rem 1.25rem; text-align: center; }
.admin-empty-state h3 { margin: 0; color: #1d3461; font-family: 'Poppins', sans-serif; font-size: 1.05rem; }
.admin-empty-state p { max-width: 30rem; margin: 0 0 .6rem; color: #68778d; font-size: .85rem; }
.admin-clear-filters { min-height: 40px; padding: .5rem .7rem; border: 0; background: transparent; color: #28548e; font: inherit; font-size: .8rem; font-weight: 700; cursor: pointer; }
.admin-clear-filters:hover { text-decoration: underline; }
@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analytics-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analytics-grid { grid-template-columns: 1fr; }
  .action-grid { grid-template-columns: 1fr; }
}
@media (max-width: 620px) {
  .stats-grid { grid-template-columns: 1fr; }
  .violation-chart__key { grid-template-columns: 1fr; }
  .device-chart { flex-direction: column; align-items: stretch; }
  .device-chart__donut { align-self: center; width: 170px; }
  .analytics-heading { align-items: start; flex-direction: column; }
  .analytics-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analytics-panel { padding: 1.1rem; }
  .institute-row { grid-template-columns: minmax(0, 1fr) 4rem; gap: .5rem; }
  .institute-measure { grid-column: 1 / -1; grid-row: 2; }
  .institute-score { grid-column: 2; grid-row: 1; }
  .institute-identity span { display: none; }
  .overview-actions { padding: 1.2rem; }
}
.admin-inline-error { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 1rem; padding: .8rem 1rem; border: 1px solid #fecaca; border-radius: 10px; background: #fef2f2; color: #991b1b; font-size: .85rem; }
.admin-inline-error button { border: 0; background: transparent; color: inherit; font: inherit; font-weight: 700; cursor: pointer; }
.admin-filter { min-height: 41px; padding: .55rem .85rem; border: 1px solid #d5dfeb; border-radius: 10px; background-color: #fff; color: #334155; font: inherit; font-size: .85rem; }
.admin-filter:is(select) { padding-right: 2.65rem; }
.admin-filters { display: flex; justify-content: flex-start; align-items: flex-end; flex-wrap: wrap; gap: .75rem; margin-bottom: 1rem; }
.admin-filter-field { display: grid; gap: .35rem; flex: 1 1 250px; min-width: min(100%, 240px); color: #475569; font-size: .75rem; font-weight: 700; }
.admin-filters > .admin-filter { flex: 0 1 195px; width: 195px; min-width: 0; }
.admin-filters > .admin-filter:last-of-type { flex-basis: 230px; width: 230px; }
.admin-filter-field .moodle-search { width: 100%; }
.table-skeleton { display: grid; gap: .35rem; padding: 1rem; }
.table-skeleton .skeleton { margin-bottom: 0; }
.admin-entry-form { margin-bottom: 1.25rem; border: 1px solid #dce5f0; border-radius: 16px; background: #fff; padding: 1.5rem; box-shadow: 0 10px 30px rgba(15, 23, 42, .055); }
.entry-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.entry-heading .form-title { margin: 0 0 .25rem; color: #142849; }
.entry-heading p { margin: 0; color: #64748b; font-size: .82rem; }
.entry-close { border: 0; background: transparent; color: #64748b; font-size: 1.5rem; line-height: 1; cursor: pointer; }
.admin-entry-form .inline-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .9rem; }
.entry-field { display: grid; gap: .35rem; min-width: 0; color: #475569; font-size: .75rem; font-weight: 700; }
.entry-actions { display: flex; justify-content: flex-end; gap: .65rem; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid #e8edf5; }
.entry-field input, .entry-field select { width: 100%; min-height: 41px; border: 1px solid #d5dfeb; border-radius: 9px; padding: .55rem .7rem; background: white; color: #142849; font: inherit; font-size: .84rem; }
.entry-field select { appearance: none; padding-right: 2.65rem; background-image: var(--select-chevron); background-repeat: no-repeat; background-position: right .95rem center; background-size: .95rem; }
.entry-field input:focus, .entry-field select:focus, .admin-filter:focus { border-color: #1d3461; outline: 3px solid rgba(29, 52, 97, .14); }
.institute-picker { max-width: 200px; width: 100%; font-size: .76rem; }
.form-error { margin: .8rem 0 0; color: #b91c1c; font-size: .82rem; }
.row-action { border: 1px solid #cbd5e1; border-radius: 8px; padding: .45rem .7rem; background: white; color: #334155; font: inherit; font-size: .76rem; font-weight: 700; cursor: pointer; white-space: nowrap; }
.instructor-row-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: .4rem; }
.instructor-email-dialog { display: grid; gap: 1rem; width: min(100%, 490px); }
.instructor-email-help { margin: -.35rem 0 0; color: #64748b; font-size: .84rem; }
.gaze-model-panel { max-width: 760px; padding: 1.5rem; border: 1px solid #dce5f0; border-radius: 16px; background: #fff; box-shadow: 0 10px 30px rgba(15,23,42,.055); }
.gaze-model-current { margin: 0 0 1rem; color: #52647e; }
.gaze-model-current strong { color: #172b4a; }
.gaze-model-options { display: grid; gap: .65rem; }
.gaze-model-option { display: flex; align-items: center; gap: .85rem; padding: .9rem 1rem; border: 1px solid #dce5f0; border-radius: 11px; cursor: pointer; }
.gaze-model-option--selected { border-color: #365588; background: #f5f8fc; }
.gaze-model-option--disabled { opacity: .55; cursor: not-allowed; }
.gaze-model-option input { accent-color: #1d3461; }
.gaze-model-option__copy { display: grid; gap: .15rem; flex: 1; color: #172b4a; }
.gaze-model-option__copy small, .gaze-model-note { color: #68778d; font-size: .8rem; }
.gaze-model-recommended { color: #1d3461; font-size: .72rem; font-weight: 700; }
.gaze-model-note { margin: .9rem 0 0; }
.row-action--danger { border-color: #fecaca; color: #b91c1c; }
.row-action--restore { border-color: #bbdfc8; color: #166534; }
.row-action:disabled { opacity: .55; cursor: wait; }
.admin-people-page .data-table-container { border: 1px solid #dfe6ef; border-radius: 16px; background: #fff; box-shadow: 0 10px 30px rgba(15, 23, 42, .055); }
.admin-people-page .data-table { min-width: 830px; }
.admin-people-page .data-table th { padding: .95rem 1.1rem; background: #f6f8fb; color: #52647e; font-size: .69rem; }
.admin-people-page .data-table td { padding: 1rem 1.1rem; font-size: .84rem; }
.admin-people-page .data-table tbody tr:hover td { background: #f8fafd; }
.review-backdrop { position: fixed; inset: 0; z-index: 1000001; display: grid; place-items: center; padding: 1rem; background: rgba(15,23,42,.58); }
.review-dialog { width: min(100%, 570px); max-height: calc(100vh - 2rem); overflow: auto; padding: 1.5rem; border-radius: 18px; background: white; box-shadow: 0 24px 70px rgba(15,23,42,.25); }
.review-heading { display: flex; justify-content: space-between; gap: 1rem; }
.review-heading h2 { margin: 0; color: #142849; font-size: 1.15rem; }
.review-heading p:last-child { margin: .2rem 0 1rem; color: #64748b; font-size: .82rem; }
.review-eyebrow { margin: 0 0 .4rem; color: #42618a; font-size: .67rem; font-weight: 700; letter-spacing: .12em; }
.review-photo { display: grid; place-items: center; min-height: 240px; max-height: 55vh; overflow: hidden; border-radius: 12px; background: #f1f5f9; }
.review-photo img { display: block; max-width: 100%; max-height: 55vh; object-fit: contain; }
.review-photo p { padding: 1rem; color: #64748b; text-align: center; }
.review-guidance { margin: 1rem 0; color: #536276; font-size: .82rem; line-height: 1.5; }
.review-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: .55rem; }
@media (max-width: 700px) { .review-actions > button { flex: 1 1 auto; } }

.modal-backdrop {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}

/* ─── Face ID column ─────────────────────────────────────── */
.face-cell {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.25rem 0;
}

.face-cell-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.face-btn-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: nowrap;
}

.face-thumb-wrap {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #e2e8f0;
  background: #f8fafc;
}
.face-thumb--pending { border-color: #3b82f6; background: #eff6ff; }
.face-thumb--approved { border-color: #22c55e; background: #f0fdf4; }

.face-thumb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.face-thumb-placeholder { font-size: 1.1rem; color: #94a3b8; }

.face-actions {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.face-label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.face-label--pending  { color: #2563eb; }
.face-label--approved { color: #15803d; }
.face-label--none     { color: #94a3b8; font-size: 0.8rem; font-weight: 500; text-transform: none; }

.face-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.22rem 0.65rem;
  border-radius: 6px;
  border: none;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s;
}
.face-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.face-btn--approve { background: #dcfce7; color: #15803d; }
.face-btn--approve:hover:not(:disabled) { background: #bbf7d0; }
.face-btn--reject  { background: #fee2e2; color: #b91c1c; }
.face-btn--reject:hover:not(:disabled)  { background: #fecaca; }

/* toggle switch */
.face-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  cursor: pointer;
  user-select: none;
}
.face-toggle input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.face-toggle input:focus-visible + .face-toggle-slider { outline: 3px solid #93c5fd; outline-offset: 2px; }
.face-toggle-slider {
  width: 30px; height: 16px;
  border-radius: 999px;
  background: #cbd5e1;
  position: relative;
  flex-shrink: 0;
  transition: background 0.2s;
}
.face-toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px; left: 2px;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.2s;
}
.face-toggle input:checked + .face-toggle-slider { background: #6366f1; }
.face-toggle input:checked + .face-toggle-slider::after { transform: translateX(14px); }
.face-toggle-label { font-size: 0.76rem; font-weight: 600; color: #475569; white-space: nowrap; }

@media (max-width: 760px) {
  .admin-course-row { grid-template-columns: 1fr; }
  .dashboard-role--admin .sidebar-nav { flex: 1 1 auto; justify-content: space-around; }
  .dashboard-role--admin .sidebar-footer-nav { flex: 0 0 auto; }
  .dashboard-role--admin .nav-count { display: none; }
  .admin-section-heading { align-items: stretch; flex-direction: column; }
  .admin-page-tabs .course-tab { flex: 1 1 0; justify-content: center; padding: .85rem .65rem; font-size: .8rem; }
  .admin-filters .admin-filter, .admin-filter-field { width: 100%; }
}
@media (max-width: 620px) {
  .admin-course-row__assignment { grid-template-columns: 1fr; }
  .admin-course-save { width: 100%; }
  .admin-entry-form .inline-form { grid-template-columns: 1fr; }
  .entry-actions > button { flex: 1 1 0; }
}
</style>
