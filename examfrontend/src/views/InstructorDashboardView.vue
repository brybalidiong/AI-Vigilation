<template>
  <div class="app-wrapper dashboard-role dashboard-role--instructor">
    <div class="dashboard-container">

      <!-- LEFT SIDEBAR -->
      <aside class="sidebar">
        <div class="sidebar-logo">
          <span class="sidebar-brand-mark" aria-hidden="true"><img src="/branding/ai-vigilation-mark.png" alt="" /></span>
          <span class="sidebar-brand-lockup">
            <span class="sidebar-brand-name">AI-Vigilation</span>
            <span class="sidebar-brand-context">Instructor workspace</span>
          </span>
        </div>
        <nav class="sidebar-nav">
          <a href="#" class="nav-item" :class="{ active: activeNav === 'dashboard' }" @click.prevent="goDashboard">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect></svg>
            Dashboard
          </a>
          <a href="#" class="nav-item" :class="{ active: activeNav === 'courses' }" @click.prevent="goCourses">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            Courses
          </a>
          <a href="#" class="nav-item" :class="{ active: activeNav === 'archive' }" @click.prevent="goArchive">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v12h14V8M10 12h4"/></svg>
            Archive
            <span v-if="archivedCourses.length" class="nav-count">{{ archivedCourses.length }}</span>
          </a>
        </nav>
        <div class="sidebar-footer-nav">
          <div class="sidebar-user-info">
            <div class="sidebar-user-avatar">{{ instructorName[0]?.toUpperCase() || 'I' }}</div>
            <div class="sidebar-user-text">
              <span class="sidebar-user-name">{{ instructorName }}</span>
              <span class="sidebar-user-role">{{ instructorEmail }}</span>
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
        <header class="main-header" :class="{ 'main-header--tight': activeNav === 'courses' }" v-show="!(activeNav === 'courses' && isCourseDetailRoute)">
          <div class="header-titles">
            <template v-if="activeNav === 'courses' && isCourseDetailRoute">
              <button type="button" class="cw-back-btn cw-back-btn--light" @click="goCourses" id="back-to-courses">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                Back
              </button>
              <div class="cw-title-row">
                <span v-if="selectedCourse" class="cw-code-pill">{{ selectedCourse.code }}</span>
                <h1>{{ selectedCourse?.name || activeCourseLabel }}</h1>
              </div>
              <p class="header-sub">{{ courseDetailMeta }}</p>
            </template>
            <template v-else>
              <span class="dashboard-eyebrow">{{ currentDate }}</span>
              <h1>{{ dashboardTitle }}</h1>
              <p v-if="activeNav === 'settings'" class="header-sub">Your personal details and account information.</p>
              <p v-else-if="activeNav === 'courses'" class="header-sub">Open your assigned courses to run exams and enroll students.</p>
              <p v-else-if="activeNav === 'archive'" class="header-sub">Courses you have set aside. Restore one to return it to your active list.</p>
              <p v-else class="header-sub">See upcoming exams and jump into a course quickly.</p>
            </template>
          </div>
          <div class="header-actions">
            <div class="role-pill">Instructor</div>
          </div>
        </header>


        <!-- DASHBOARD TAB -->
        <template v-if="activeNav === 'dashboard'">
          <section class="dashboard-welcome">
            <div class="dashboard-welcome__copy">
              <span class="dashboard-welcome__eyebrow">Teaching overview</span>
              <h2>Keep every assessment on track.</h2>
              <p>Manage your courses, monitor scheduled exams, and review student progress from one workspace.</p>
            </div>
            <button type="button" class="dashboard-welcome__action" @click="goCourses">
              Manage courses
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
            </button>
          </section>

          <div class="moodle-card dashboard-agenda">
            <div class="agenda-header">
              <div class="agenda-header__copy">
                <h2 class="moodle-section-title">Exam calendar</h2>
                <p class="agenda-header__subtitle">Select a date to see its exams.</p>
              </div>
              <button type="button" class="agenda-view-all" @click="goCourses">
                View all
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
              </button>
            </div>

            <div class="exam-calendar-toolbar">
              <div class="agenda-search-wrap">
                <svg class="agenda-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>
                </svg>
                <input v-model.trim="timelineSearch" type="search" class="moodle-search agenda-search" aria-label="Search upcoming exams" placeholder="Search upcoming exams" />
              </div>
              <div class="exam-calendar-nav" aria-label="Calendar navigation">
                <button type="button" class="exam-calendar-nav__arrow" aria-label="Previous month" @click="moveCalendarMonth(-1)">‹</button>
                <strong>{{ calendarMonthLabel }}</strong>
                <button type="button" class="exam-calendar-nav__arrow" aria-label="Next month" @click="moveCalendarMonth(1)">›</button>
                <button type="button" class="exam-calendar-nav__today" @click="selectCalendarToday">Today</button>
              </div>
            </div>

            <div class="exam-calendar-layout">
              <div class="exam-calendar-grid" aria-label="Exam dates">
                <span v-for="weekday in calendarWeekdays" :key="weekday" class="exam-calendar-weekday">{{ weekday }}</span>
                <template v-for="day in calendarDays" :key="day.key">
                  <span v-if="day.blank" class="exam-calendar-blank" aria-hidden="true"></span>
                  <button
                    v-else
                    type="button"
                    class="exam-calendar-day"
                    :class="{ 'is-selected': selectedCalendarDay === day.key, 'is-today': todayCalendarKey === day.key, 'has-exams': day.count > 0 }"
                    :aria-pressed="selectedCalendarDay === day.key"
                    :aria-label="`${day.date.toLocaleDateString(undefined, { dateStyle: 'full' })}, ${day.count} exam${day.count === 1 ? '' : 's'}`"
                    @click="selectedCalendarDay = day.key"
                  >
                    <span class="exam-calendar-day__number">{{ day.day }}</span>
                    <span v-if="day.count" class="exam-calendar-day__count">{{ day.count }}</span>
                  </button>
                </template>
              </div>

              <section class="exam-calendar-detail" aria-live="polite">
                <div class="exam-calendar-detail__heading">
                  <div>
                    <span class="exam-calendar-detail__eyebrow">Selected day</span>
                    <h3>{{ selectedCalendarLabel }}</h3>
                  </div>
                  <span class="exam-calendar-detail__total">{{ selectedCalendarExams.length }} exam{{ selectedCalendarExams.length === 1 ? '' : 's' }}</span>
                </div>
                <div v-if="upcomingLoading" class="exam-calendar-detail__list">
                  <SkeletonLoader type="row" v-for="i in 2" :key="i" />
                </div>
                <div v-else-if="selectedCalendarExams.length" class="exam-calendar-detail__list">
                  <article v-for="exam in selectedCalendarExams" :key="`upcoming-${exam.subject_id}-${exam.id}`" class="exam-calendar-event">
                    <div class="exam-calendar-event__top">
                      <span class="exam-calendar-event__time">{{ calendarExamTimeLabel(exam) }}</span>
                      <span class="exam-calendar-status" :class="exam.is_final ? 'badge-active' : 'badge-upcoming'">{{ exam.is_final ? 'Published' : 'Draft' }}</span>
                    </div>
                    <h4>{{ formatDisplayTitle(exam.title) }}</h4>
                    <p>{{ formatDisplayTitle(`${exam.subject_code} ${exam.subject_name}`) }}</p>
                    <div class="exam-calendar-event__actions">
                      <button type="button" class="moodle-btn-ghost" @click="openExamStats(exam)">View Stats</button>
                    </div>
                  </article>
                </div>
                <div v-else class="exam-calendar-detail__empty">
                  <p>{{ filteredUpcomingExams.length ? 'No exams on this date.' : 'No upcoming exams found.' }}</p>
                  <button v-if="filteredUpcomingExams.length" type="button" @click="selectNextCalendarExam">Show next exam</button>
                </div>
              </section>
            </div>
          </div>
        </template>

        <!-- SETTINGS TAB -->
        <template v-else-if="activeNav === 'settings'">
          <div class="workspace-area">
            <UserProfileSettings 
              :user="currentUser" 
              :loading="profileLoading"
              :errorMsg="profileError"
              :successMsg="profileSuccess"
              @save-profile="handleProfileUpdate"
              @dismiss-notice="profileError = ''; profileSuccess = ''"
            />
          </div>
        </template>


        <!-- COURSES TAB (No Course Opened) -->
        <template v-if="activeNav === 'courses' && !isCourseDetailRoute">
          <div class="courses-page">

            <div class="courses-command">
              <p class="courses-command__meta">
                <strong>{{ coursesSummary.total }}</strong>
                {{ coursesSummary.total === 1 ? 'course' : 'courses' }}
                <span aria-hidden="true">·</span>
                <strong>{{ coursesSummary.students }}</strong>
                enrolled
                <template v-if="courseSearch">
                  <span aria-hidden="true">·</span>
                  {{ coursesSummary.filtered }} matching “{{ courseSearch }}”
                </template>
              </p>
              <div class="courses-command__controls">
                <div class="courses-search-wrap">
                  <svg class="courses-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <input
                    v-model.trim="courseSearch"
                    type="search"
                    class="courses-search-input"
                    placeholder="Search by name or code"
                    aria-label="Search courses"
                  />
                </div>
                <label class="courses-sort-label">
                  <span class="visually-hidden">Sort courses</span>
                  <select v-model="courseSort" class="courses-sort-select" aria-label="Sort courses">
                    <option value="name_asc">A → Z</option>
                    <option value="name_desc">Z → A</option>
                  </select>
                </label>
              </div>
            </div>

            <!-- Course grid -->
            <TransitionGroup name="list" tag="div" class="courses-grid">
              <template v-if="subjectsLoading">
                <SkeletonLoader type="card" v-for="i in 3" :key="`skel-${i}`" />
              </template>
              <EmptyState
                v-else-if="displayedCourses.length === 0 && courseSearch"
                style="grid-column: 1 / -1;"
                title="No matching courses"
                description="Try another name or code. Your administrator assigns courses to instructors."
                icon='<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>'
              >
                <template #actions>
                  <button type="button" class="ghost-btn" @click="courseSearch = ''">Clear search</button>
                </template>
              </EmptyState>
              <EmptyState
                v-else-if="displayedCourses.length === 0"
                style="grid-column: 1 / -1;"
                title="No active courses"
                description="Your administrator assigns courses to you. Archived courses are available on the Archive page."
                icon='<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line>'
              />
              <template v-else>
                <CourseCard
                  v-for="(s, index) in displayedCourses"
                  :key="s.id"
                  :folderClass="['folder-1','folder-2','folder-3','folder-4','folder-5'][index % 5]"
                  :code="s.code"
                  :name="s.name"
                  :students="s.student_count"
                  :photo="s.display_photo"
                  @click="openCourse(s.id)"
                />
              </template>
            </TransitionGroup>
          </div>
        </template>

        <template v-if="activeNav === 'archive'">
          <div class="courses-page">
            <div class="courses-command archive-heading">
              <div><h2>Archived courses</h2><p>Only your course list is affected. Exams and student records remain available to assigned instructors.</p></div>
              <span>{{ archivedCourses.length }} {{ archivedCourses.length === 1 ? 'course' : 'courses' }}</span>
            </div>
            <div v-if="subjectsLoading" class="courses-grid"><SkeletonLoader type="card" v-for="i in 2" :key="`archive-skel-${i}`" /></div>
            <EmptyState
              v-else-if="!archivedCourses.length"
              title="Your archive is empty"
              description="Courses you archive will appear here until you restore them."
              icon='<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v12h14V8M10 12h4"/>'
            />
            <div v-else class="archive-grid">
              <article v-for="course in archivedCourses" :key="course.id" class="archive-course-card">
                <span class="archive-course-card__code">{{ course.code }}</span>
                <h3>{{ course.name }}</h3>
                <p>{{ course.student_count }} {{ course.student_count === 1 ? 'student' : 'students' }} enrolled</p>
                <button type="button" class="archive-course-card__restore" :disabled="archiveBusyId === course.id" @click="restoreSubject(course)">{{ archiveBusyId === course.id ? 'Restoring…' : 'Restore course' }}</button>
              </article>
            </div>
          </div>
        </template>

        <!-- COURSE WORKSPACE -->
        <template v-if="activeNav === 'courses' && isCourseDetailRoute">
          <div class="course-workspace">

          <!-- ── HERO BANNER ── -->
          <div class="cw-hero">
            <div v-if="selectedCourse?.display_photo" class="cw-hero__backdrop" :style="{ backgroundImage: `url(${selectedCourse.display_photo})` }"></div>
            <div class="cw-hero__content">
              <div class="cw-hero__nav">
                <button type="button" class="cw-back-btn" @click="goCourses" id="back-to-courses-hero">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                  Back
                </button>
                <details ref="courseActionsMenu" class="cw-actions-menu" @keydown.esc.prevent="closeCourseActionsMenu">
                  <summary aria-label="Course actions" title="Course actions">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="5" r="1.75"/><circle cx="12" cy="12" r="1.75"/><circle cx="12" cy="19" r="1.75"/></svg>
                  </summary>
                  <div class="cw-actions-menu__popup">
                    <button type="button" id="change-course-banner-btn" :disabled="bannerUploading" @click="openCourseBannerPicker">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
                      {{ bannerUploading ? 'Uploading…' : 'Change banner' }}
                    </button>
                    <button type="button" id="archive-course-btn" @click="requestArchiveSubject">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v12h14V8M10 12h4"/></svg>
                      Archive course
                    </button>
                  </div>
                </details>
                <input ref="courseBannerInput" class="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" aria-label="Choose course banner" @change="uploadCourseBanner" />
              </div>
              <div class="cw-hero__main">
                <div>
                  <div class="cw-hero__code">{{ selectedCourse?.code || '' }}</div>
                  <h2 class="cw-hero__title">{{ selectedCourse?.name || '' }}</h2>
                </div>
              </div>
              <div class="cw-hero__stats">
                <span class="cw-stat-chip">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                  <strong>{{ selectedCourse?.student_count ?? 0 }}</strong>
                  {{ selectedCourse?.student_count === 1 ? 'student' : 'students' }}
                </span>
                <span class="cw-stat-chip">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  <strong>{{ courseDetailStats.exams }}</strong>
                  {{ courseDetailStats.exams === 1 ? 'exam' : 'exams' }}
                </span>
              </div>
            </div>
          </div>

          <div class="course-tabs-card">
            <div class="course-tabstrip" role="tablist" aria-label="Course sections">
              <button
                type="button"
                role="tab"
                class="course-tab"
                :class="{ active: activeCourseTab === 'uploaded-exams' }"
                :aria-selected="activeCourseTab === 'uploaded-exams'"
                @click="activeCourseTab = 'uploaded-exams'"
                id="tab-uploaded-exams"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                Exams
                <span class="course-tab__count">{{ courseDetailStats.exams }}</span>
              </button>
              <button
                type="button"
                role="tab"
                class="course-tab"
                :class="{ active: activeCourseTab === 'question-bank' }"
                :aria-selected="activeCourseTab === 'question-bank'"
                @click="activeCourseTab = 'question-bank'"
                id="tab-question-bank"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>
                Question Bank
                <span class="course-tab__count">{{ bankQuestions.length }}</span>
              </button>
              <button
                type="button"
                role="tab"
                class="course-tab"
                :class="{ active: activeCourseTab === 'sets' }"
                :aria-selected="activeCourseTab === 'sets'"
                @click="activeCourseTab = 'sets'"
                id="tab-sets"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
                Enroll Students
                <span class="course-tab__count">{{ courseDetailStats.students }}</span>
              </button>
              <button
                type="button"
                role="tab"
                class="course-tab"
                :class="{ active: activeCourseTab === 'exam-progress' }"
                :aria-selected="activeCourseTab === 'exam-progress'"
                @click="activeCourseTab = 'exam-progress'"
                id="tab-exam-progress"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                Exam Progress
              </button>
            </div>

            <div class="course-tab-panel course-exam-scroll" role="tabpanel">

          <!-- TAB: UPLOADED EXAMS -->
          <div v-if="activeCourseTab === 'uploaded-exams'" class="workspace-area">

            <div class="panel-toolbar">
              <div class="panel-toolbar__filters">
                <div class="filter-chips" role="group" aria-label="Filter exams">
                  <button type="button" class="filter-chip" :class="{ active: examStatusFilter === 'all' }" @click="examStatusFilter = 'all'">All</button>
                  <button type="button" class="filter-chip" :class="{ active: examStatusFilter === 'published' }" @click="examStatusFilter = 'published'">Published</button>
                  <button type="button" class="filter-chip" :class="{ active: examStatusFilter === 'draft' }" @click="examStatusFilter = 'draft'">Draft</button>
                </div>
                <div class="courses-search-wrap panel-search">
                  <svg class="courses-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <input v-model.trim="examSearch" type="search" class="courses-search-input" placeholder="Search exams" aria-label="Search exams" />
                </div>
              </div>
              <button type="button" class="new-course-btn" @click="showUploadExamPanel = !showUploadExamPanel" id="toggle-upload-exam">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M12 3v12m-5-5 5-5 5 5"/></svg>
                {{ showUploadExamPanel ? 'Cancel' : 'Create exam' }}
              </button>
            </div>

            <!-- Collapsible Upload Form -->
            <transition name="slide-down">
              <div v-if="showUploadExamPanel" class="create-panel" id="upload-exam-panel">
                <div class="create-panel__header">
                  <div class="create-panel__icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M12 3v12m-5-5 5-5 5 5"/></svg>
                  </div>
                  <div>
                    <h3 class="create-panel__title">Create New Exam</h3>
                    <p class="create-panel__sub">Set the exam schedule and rules, then choose questions from this course's Question Bank.</p>
                  </div>
                </div>
                <form @submit.prevent="createExamSet">
                  <div class="upload-exam-grid">
                    <div class="create-panel__field" style="grid-column: 1 / -1;">
                      <label class="create-panel__label" for="new-exam-title">Exam Title</label>
                      <input id="new-exam-title" v-model="newExamTitle" type="text" class="create-panel__input" placeholder="e.g. Midterm Examination" required />
                    </div>
                    <div class="create-panel__field">
                      <label class="create-panel__label" for="new-exam-start">Starts At</label>
                      <input id="new-exam-start" v-model="newExamStartAt" type="datetime-local" class="create-panel__input" required />
                    </div>
                    <div class="create-panel__field">
                      <label class="create-panel__label" for="new-exam-end">Ends At</label>
                      <input id="new-exam-end" v-model="newExamDueAt" type="datetime-local" class="create-panel__input" required />
                    </div>
                    <div class="create-panel__field">
                      <label class="create-panel__label" for="new-exam-attempts">Max Attempts</label>
                      <input id="new-exam-attempts" v-model="newExamMaxAttempts" type="number" min="1" step="1" class="create-panel__input" required />
                    </div>
                    <div class="create-panel__field">
                      <label class="create-panel__label" for="new-exam-time-limit">Time Limit <span style="font-weight:400;color:#94a3b8">(mins, 0 = none)</span></label>
                      <input id="new-exam-time-limit" v-model="newExamTimeLimit" type="number" min="0" step="1" class="create-panel__input" placeholder="60" required />
                    </div>
                    <div class="create-panel__field" style="grid-column: 1 / -1;">
                      <label class="create-panel__label" for="new-exam-backtracking">Question navigation</label>
                      <select id="new-exam-backtracking" v-model="newExamAllowBacktracking" class="create-panel__input">
                        <option :value="true">Allow students to return to previous questions</option>
                        <option :value="false">Do not allow students to return to previous questions</option>
                      </select>
                      <small style="color:#64748b;line-height:1.4;">When returning is disabled, selecting Next saves that answer and locks the question for this attempt.</small>
                    </div>
                    <div class="create-panel__field">
                      <label class="create-panel__label" for="new-exam-section">Assign to Section</label>
                      <select id="new-exam-section" v-model="newExamAssignedSet" class="create-panel__input">
                        <option value="">All Sets (Entire Course)</option>
                        <option v-for="s in subjectSets" :key="s.id" :value="s.id">{{ s.name }}</option>
                      </select>
                    </div>
                  </div>
                  <div class="create-panel__actions" style="margin-top:1.5rem;">
                    <p style="font-size:0.82rem;color:#64748b;flex:1;">Create or import questions in the Question Bank tab. Students see this exam after you publish it.</p>
                    <button type="button" class="ghost-btn" @click="showUploadExamPanel = false">Cancel</button>
                    <button type="submit" class="primary-btn" :disabled="examSetsLoading || examUploading">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M12 3v12m-5-5 5-5 5 5"/></svg>
                      {{ examUploading ? 'Creating…' : 'Create exam' }}
                    </button>
                  </div>
                </form>
              </div>
            </transition>

          <div class="moodle-timeline-list course-exam-scroll" style="margin-top: 1.25rem;">
            <template v-if="examSetsLoading">
              <SkeletonLoader type="row" v-for="i in 3" :key="`ex-${i}`" />
            </template>
            <EmptyState 
              v-else-if="examSets.length === 0" 
              title="No exams yet" 
              description="Create an exam draft, then choose questions from the course bank."
              icon='<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline>'
            >
              <template #actions>
                <button type="button" class="primary-btn" @click="showUploadExamPanel = true">Create exam</button>
              </template>
            </EmptyState>
            <EmptyState
              v-else-if="displayedExams.length === 0"
              title="No exams match"
              description="Clear the search or switch the Published / Draft filter."
              icon='<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>'
            >
              <template #actions>
                <button type="button" class="ghost-btn" @click="examSearch = ''; examStatusFilter = 'all'">Reset filters</button>
              </template>
            </EmptyState>
            <template v-else>
              <ExamRow
                v-for="exam in displayedExams"
                :key="exam.id"
                :dateIso="examTimelineDisplayAt(exam)"
                :timeText="formatExamTimelineTime(exam)"
                :title="formatDisplayTitle(exam.title)"
                :subtitle="toDisplayDue(exam)"
                :status="exam.is_final ? examLifecycleLabel(exam) : 'Draft'"
                :statusClass="exam.is_final ? ('status-' + examLifecycle(exam)) : 'status-draft'"
              >
                <template #actions>
                  <button class="moodle-btn-ghost" type="button" @click="openManageQuestions(exam)">
                    Questions
                  </button>
                  <button class="moodle-btn-ghost" type="button" @click="openExamStats(exam)">
                    Stats
                  </button>
                  <button class="moodle-btn-ghost moodle-btn-ghost--danger" type="button" @click="requestRemoveExamSet(exam.id)" aria-label="Delete exam">
                    Delete
                  </button>
                </template>
              </ExamRow>
            </template>
          </div>
          </div>

          <!-- TAB: COURSE QUESTION BANK -->
          <div v-if="activeCourseTab === 'question-bank'" class="workspace-area bank-workspace">
            <div class="bank-heading">
              <div>
                <span class="bank-eyebrow">{{ selectedCourse?.code || 'COURSE' }} · QUESTION LIBRARY</span>
                <h2>Question Bank</h2>
                <p>Create and organize reusable questions for {{ selectedCourse?.name }}. Choose them when building a draft exam.</p>
              </div>
              <div class="bank-heading__stats">
                <span><strong>{{ bankBatches.length }}</strong> {{ bankBatches.length === 1 ? 'batch' : 'batches' }}</span>
                <span><strong>{{ bankQuestions.length }}</strong> {{ bankQuestions.length === 1 ? 'question' : 'questions' }}</span>
              </div>
            </div>
            <div class="bank-layout">
              <section class="bank-list-panel">
                <div class="bank-panel-heading">
                  <span class="bank-panel-heading__icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 5h16v14H4z"/><path d="M8 9h8M8 13h8"/></svg></span>
                  <div><span class="bank-eyebrow">YOUR COLLECTION</span><h3>Saved batches</h3></div>
                </div>
                <div class="bank-filter-row">
                  <input v-model.trim="bankSearch" type="search" class="create-panel__input" placeholder="Search questions" aria-label="Search bank questions" />
                  <select v-model="bankTypeFilter" class="create-panel__input" aria-label="Filter bank by question type">
                    <option value="all">All types</option>
                    <option value="multiple_choice">Multiple choice</option>
                    <option value="identification">Identification</option>
                    <option value="enumeration">Enumeration</option>
                    <option value="essay">Essay</option>
                  </select>
                </div>
                <p class="bank-help">Browse questions by batch. Deleting a batch leaves existing exams unchanged.</p>
                <template v-if="bankLoading"><SkeletonLoader v-for="i in 3" :key="`bank-skel-${i}`" type="row" /></template>
                <EmptyState v-else-if="bankQuestions.length === 0" title="No questions in this course" description="Add a question or import a file to build the bank." />
                <EmptyState v-else-if="filteredBankBatches.length === 0" title="No matching questions" description="Try another search or question type." />
                <div v-else class="bank-item-list">
                  <details v-for="(batch, index) in filteredBankBatches" :key="batch.id" class="bank-batch" :open="filteredBankBatches.length === 1">
                    <summary><span class="bank-batch__index">{{ String(index + 1).padStart(2, '0') }}</span><strong>{{ batch.name }}</strong><span>{{ batch.questions.length }} questions</span></summary>
                    <div class="bank-batch__actions"><button type="button" class="bank-item__delete" :disabled="bankSaving" @click="requestDeleteBankBatch(batch)">Delete batch</button></div>
                    <article v-for="item in batch.questions" :key="item.id" class="bank-item">
                      <div class="bank-item__main">
                        <span class="bank-item__type">{{ questionTypeLabel(item.question_type) }}</span>
                        <p>{{ item.question_text }}</p>
                        <details class="bank-item__details">
                          <summary>Show answer details</summary>
                          <ul v-if="item.choices?.length"><li v-for="choice in item.choices" :key="choice">{{ choice }}</li></ul>
                          <span>{{ item.correct_answer ? `Answer: ${item.correct_answer}` : 'Manual grading' }}</span>
                        </details>
                      </div>
                      <button type="button" class="bank-item__delete" :disabled="bankSaving" @click="requestDeleteBankQuestion(item)">Delete</button>
                    </article>
                  </details>
                </div>
              </section>
              <div class="bank-editor">
                <div class="bank-editor-switch" role="tablist" aria-label="Question bank actions">
                  <button type="button" role="tab" :aria-selected="bankEditorMode === 'create'" :class="{ active: bankEditorMode === 'create' }" @click="bankEditorMode = 'create'">Create question</button>
                  <button type="button" role="tab" :aria-selected="bankEditorMode === 'import'" :class="{ active: bankEditorMode === 'import' }" @click="bankEditorMode = 'import'">Import batch</button>
                </div>
                <section v-if="bankEditorMode === 'create'" class="bank-editor-card">
                  <div class="bank-panel-heading"><span class="bank-panel-heading__icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9M16.5 3.5a2 2 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg></span><div><span class="bank-eyebrow">QUESTION EDITOR</span><h3>Create a question</h3></div></div>
                  <p>Build a question here, then select it from a batch when preparing an exam.</p>
                  <form @submit.prevent="addBankQuestion" class="bank-form">
                    <label>Batch name
                      <input v-model.trim="bankBatchName" class="create-panel__input" maxlength="160" required placeholder="e.g. Chapter 1" />
                    </label>
                    <fieldset class="bank-type-fieldset"><legend>Question type</legend><div class="bank-type-pills">
                      <label v-for="type in [{ value: 'multiple_choice', label: 'Multiple choice' }, { value: 'identification', label: 'Identification' }, { value: 'enumeration', label: 'Enumeration' }, { value: 'essay', label: 'Essay' }]" :key="type.value" :class="{ active: newQ.type === type.value }">
                        <input v-model="newQ.type" type="radio" name="bank-question-type" :value="type.value" />{{ type.label }}
                      </label>
                    </div></fieldset>
                    <label>Question prompt
                      <textarea v-model.trim="newQ.text" class="create-panel__input bank-textarea" required placeholder="Enter the question students will see"></textarea>
                    </label>
                    <template v-if="newQ.type === 'multiple_choice'">
                      <fieldset class="bank-choice-fieldset">
                        <legend>Choices · select the correct answer</legend>
                        <div v-for="(choice, index) in newQ.choices" :key="index" class="bank-choice-row">
                          <input v-model="newQ.correctIdx" type="radio" name="bank-correct-choice" :value="index" :aria-label="`Choice ${index + 1} is correct`" />
                          <input v-model.trim="newQ.choices[index]" class="create-panel__input" :placeholder="`Choice ${index + 1}`" required />
                          <button v-if="newQ.choices.length > 2" type="button" class="bank-remove-choice" @click="removeChoice(index)" aria-label="Remove choice">×</button>
                        </div>
                        <button v-if="newQ.choices.length < 6" type="button" class="bank-text-button" @click="addChoice">+ Add choice</button>
                      </fieldset>
                    </template>
                    <template v-else-if="newQ.type === 'identification'">
                      <label>Correct answer <small>(optional for manual grading)</small>
                        <input v-model.trim="newQ.correctAnswer" class="create-panel__input" />
                      </label>
                      <label class="bank-checkbox"><input v-model="newQ.caseSensitive" type="checkbox" /> Case sensitive</label>
                    </template>
                    <template v-else-if="newQ.type === 'enumeration'">
                      <fieldset class="bank-choice-fieldset">
                        <legend>Expected answers</legend>
                        <div v-for="(item, index) in newQ.enumerationItems" :key="index" class="bank-choice-row">
                          <input v-model.trim="newQ.enumerationItems[index]" class="create-panel__input" :placeholder="`Item ${index + 1}`" />
                          <button v-if="newQ.enumerationItems.length > 1" type="button" class="bank-remove-choice" @click="removeEnumerationItem(index)" aria-label="Remove item">×</button>
                        </div>
                        <button type="button" class="bank-text-button" @click="addEnumerationItem">+ Add item</button>
                      </fieldset>
                      <label>Points <small>(optional)</small><input v-model="newQ.points" type="number" min="1" class="create-panel__input" /></label>
                      <label class="bank-checkbox"><input v-model="newQ.caseSensitive" type="checkbox" /> Case sensitive</label>
                    </template>
                    <button type="submit" class="primary-btn" :disabled="bankSaving">{{ bankSaving ? 'Saving…' : 'Save to bank' }}</button>
                  </form>
                </section>
                <section v-else class="bank-editor-card">
                  <div class="bank-panel-heading"><span class="bank-panel-heading__icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 16V3m0 0-4 4m4-4 4 4M4 16v4h16v-4"/></svg></span><div><span class="bank-eyebrow">BULK UPLOAD</span><h3>Import a batch</h3></div></div>
                  <p>Upload a text file or paste questions. Aiken multiple choice uses an ANSWER letter; essay prompts are separated by blank lines.</p>
                  <form @submit.prevent="processBulkQuestions" class="bank-form">
                    <label>Batch name
                      <input v-model.trim="bankImportBatchName" class="create-panel__input" maxlength="160" placeholder="e.g. Midterm question set" />
                    </label>
                    <label>Format
                      <select v-model="bankImportFormat" class="create-panel__input"><option value="aiken">Multiple choice (Aiken)</option><option value="essay">Essay prompts</option></select>
                    </label>
                    <label>Question file (.txt)
                      <input type="file" accept=".txt" class="create-panel__input" @change="onAikenFileUpload" />
                    </label>
                    <span v-if="aikenFileName" class="bank-help">Loaded {{ aikenFileName }}</span>
                    <label>Questions to import
                      <textarea v-model="bulkText" class="create-panel__input bank-textarea" placeholder="Paste questions here" required></textarea>
                    </label>
                    <button type="submit" class="primary-btn" :disabled="bankSaving || !bulkText.trim()">{{ bankSaving ? 'Importing…' : 'Import to bank' }}</button>
                  </form>
                </section>
              </div>
            </div>
          </div>

          <!-- TAB: ENROLL STUDENTS -->
          <div v-if="activeCourseTab === 'sets'" class="workspace-area">
            <div class="enroll-tab-layout">

              <!-- LEFT: Sets sidebar -->
              <div class="enroll-sets-sidebar">
                <div class="enroll-sets-sidebar__header">
                  <span class="enroll-sets-sidebar__title">Sections</span>
                  <div class="enroll-sets-sidebar__header-actions">
                    <span class="enroll-sets-sidebar__count">{{ subjectSets.length }}</span>
                    <button type="submit" form="create-set-form" class="enroll-create-set-btn" :disabled="subjectSetsLoading" title="Add Section">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    </button>
                  </div>
                </div>

                <!-- Create set form -->
                <form class="enroll-create-set-form" @submit.prevent="createSubjectSet" id="create-set-form">
                  <input v-model="newSubjectSetName" type="text" placeholder="New section name…" required class="enroll-create-set-input" />
                </form>

                <!-- Set list -->
                <template v-if="subjectSetsLoading">
                  <SkeletonLoader type="row" v-for="i in 2" :key="`set-${i}`" />
                </template>
                <div v-else-if="subjectSets.length === 0" class="enroll-sets-empty">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                  <p>No sections yet.<br/>Create one above.</p>
                </div>
                <div v-else class="enroll-set-list">
                  <div
                    v-for="(setItem, index) in subjectSets"
                    :key="setItem.id"
                    role="button"
                    tabindex="0"
                    class="enroll-set-item"
                    :class="[`enroll-set-item--color-${(index % 4) + 1}`, { active: selectedSubjectSetId == setItem.id }]"
                    @click="selectedSubjectSetId = String(setItem.id); studentSearch = ''; fetchSubjectStudents()"
                    @keydown.enter.space.prevent="selectedSubjectSetId = String(setItem.id); studentSearch = ''; fetchSubjectStudents()"
                  >
                    <div class="enroll-set-item__dot"></div>
                    <div class="enroll-set-item__info">
                      <span class="enroll-set-item__name">{{ setItem.name }}</span>
                      <span class="enroll-set-item__count">{{ setItem.student_count }} student{{ setItem.student_count !== 1 ? 's' : '' }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- RIGHT: Enrollment panel -->
              <div class="enroll-panel">
                <!-- No set selected -->
                <div v-if="!selectedSubjectSetId" class="enroll-panel__empty">
                  <div class="enroll-panel__empty-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
                  </div>
                  <p class="enroll-panel__empty-title">Select a section</p>
                  <p class="enroll-panel__empty-sub">Pick a section on the left to enroll students and manage the class list.</p>
                </div>

                <!-- Set selected -->
                <template v-else>
                  <div class="enroll-panel__section-header">
                    <div>
                      <h3 class="enroll-panel__section-name">{{ activeSetLabel }}</h3>
                      <p class="enroll-panel__section-sub">{{ subjectStudents.length }} enrolled in this section</p>
                    </div>
                    <div class="courses-search-wrap panel-search">
                      <svg class="courses-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                      <input v-model.trim="studentSearch" type="search" class="courses-search-input" placeholder="Search students" aria-label="Search students" />
                    </div>
                  </div>

                  <div class="enroll-quick">
                    <form class="enroll-inline-form" @submit.prevent="enrollStudentToSubject">
                      <input v-model="subjectStudentEmail" type="email" placeholder="student@dnsc.edu.ph" required aria-label="Student email" />
                      <button type="submit" class="primary-btn" :disabled="studentsLoading">Enroll</button>
                    </form>
                    <button type="button" class="ghost-btn" :class="{ 'ghost-btn--on': showBatchEnroll }" @click="showBatchEnroll = !showBatchEnroll">
                      {{ showBatchEnroll ? 'Hide batch' : 'Batch enroll' }}
                    </button>
                  </div>

                  <transition name="slide-down">
                    <div v-if="showBatchEnroll" class="create-panel" style="margin-bottom: 1rem;">
                      <form class="enroll-batch-form" @submit.prevent="bulkEnrollToSet">
                        <textarea v-model="bulkEnrollEmails" rows="3" placeholder="Paste comma-separated emails: john@dnsc.edu.ph, jane@dnsc.edu.ph"></textarea>
                        <div class="enroll-batch-actions">
                          <label class="file-pick-label" style="flex: 1; margin: 0; padding: 0.4rem 0.75rem;">
                            <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="onXlsxUpload" class="file-pick-input" :disabled="bulkEnrollLoading" />
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M12 3v12m-5-5 5-5 5 5"/></svg>
                            <span class="file-pick-text">{{ bulkEnrollLoading ? 'Uploading…' : 'Upload Excel (.xlsx)' }}</span>
                          </label>
                          <button type="submit" class="primary-btn" :disabled="bulkEnrollLoading">{{ bulkEnrollLoading ? 'Processing…' : 'Enroll list' }}</button>
                        </div>
                        <p class="enroll-upload-hint">Excel files need an <strong>Email</strong> or <strong>Student Email</strong> column. Uploading starts enrollment immediately.</p>
                      </form>
                      <p class="enroll-result" v-if="bulkEnrollResult">
                        <span class="result-ok">&#10003; {{ bulkEnrollResult.added?.length || 0 }} added</span>
                        <span class="result-skip">{{ bulkEnrollResult.skipped_duplicates?.length || 0 }} skipped</span>
                        <span class="result-err" v-if="bulkEnrollResult.errors?.length">{{ bulkEnrollResult.errors.length }} errors</span>
                      </p>
                      <ul v-if="bulkEnrollResult?.errors?.length" class="enroll-import-errors">
                        <li v-for="item in bulkEnrollResult.errors.slice(0, 5)" :key="`${item.row || 'manual'}-${item.email}`">
                          <strong v-if="item.row">Row {{ item.row }}:</strong>
                          {{ item.email }} — {{ item.error }}
                        </li>
                        <li v-if="bulkEnrollResult.errors.length > 5">
                          …and {{ bulkEnrollResult.errors.length - 5 }} more error(s).
                        </li>
                      </ul>
                    </div>
                  </transition>

                  <div class="students-list">
                    <template v-if="studentsLoading">
                      <SkeletonLoader type="row" v-for="i in 3" :key="`std-${i}`" />
                    </template>
                    <div v-else-if="subjectStudents.length === 0" class="empty-state-box">
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                      <p>No students in this section yet. Enroll one above.</p>
                    </div>
                    <div v-else-if="displayedStudents.length === 0" class="empty-state-box">
                      <p>No students match “{{ studentSearch }}”.</p>
                      <button type="button" class="ghost-btn" @click="studentSearch = ''">Clear search</button>
                    </div>
                    <div v-else class="data-table-container">
                      <table class="data-table">
                        <thead>
                          <tr><th>Student</th><th style="text-align:right;">Actions</th></tr>
                        </thead>
                        <tbody>
                          <tr v-for="student in displayedStudents" :key="student.id">
                            <td>
                              <div class="student-row">
                                <div class="student-avatar">{{ (student.email || '?')[0].toUpperCase() }}</div>
                                <span class="bold-td">{{ student.email }}</span>
                              </div>
                            </td>
                            <td style="text-align:right;"><button class="remove-btn" @click="requestRemoveSubjectStudent(student.id)">Remove</button></td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </template>
              </div>

            </div>
          </div>

          <!-- TAB: EXAM PROGRESS -->
          <div v-if="activeCourseTab === 'exam-progress'" class="workspace-area">
          <div class="ep-layout">
            <template v-if="examProgressLoading">
              <SkeletonLoader type="row" v-for="i in 3" :key="`prog-${i}`" />
            </template>
            <EmptyState 
              v-else-if="examProgressRows.length === 0" 
              title="No progress data yet" 
              description="Upload exams and enroll students to start tracking scores and integrity reports." 
              icon='<line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line>'
            />
            <template v-else>
              <div class="ep-view-toolbar">
                <div class="ep-view-control">
                  <span class="ep-control-label">View by</span>
                  <div class="ep-view-toggle" role="group" aria-label="Organize exam progress">
                    <button
                      type="button"
                      :class="{ active: progressView === 'student' }"
                      :aria-pressed="progressView === 'student'"
                      @click="progressView = 'student'"
                    >Student</button>
                    <button
                      type="button"
                      :class="{ active: progressView === 'exam' }"
                      :aria-pressed="progressView === 'exam'"
                      @click="progressView = 'exam'"
                    >Exam / quiz</button>
                  </div>
                </div>
                <label class="ep-sort-control">
                  <span class="ep-control-label">Sort by</span>
                  <select v-model="progressSort" class="courses-sort-select" aria-label="Sort exam progress">
                    <option value="student_asc">Student (A–Z)</option>
                    <option value="student_desc">Student (Z–A)</option>
                    <template v-if="progressView === 'exam'">
                      <option value="score_desc">Actual score (descending)</option>
                      <option value="score_asc">Actual score (ascending)</option>
                      <option value="integrity_desc">Integrity score (descending)</option>
                      <option value="integrity_asc">Integrity score (ascending)</option>
                    </template>
                  </select>
                </label>
              </div>

              <div class="panel-toolbar">
                <div class="filter-chips" role="group" aria-label="Filter by section">
                  <button
                    v-for="setItem in progressSets"
                    :key="setItem.id"
                    type="button"
                    class="filter-chip"
                    :class="{ active: selectedProgressSetId === setItem.id }"
                    @click="selectedProgressSetId = setItem.id; selectedProgressStudentEmail = ''; progressStudentSearch = ''"
                  >
                    {{ setItem.name }}
                    <span class="filter-chip__count">{{ setItem.studentCount }}</span>
                  </button>
                </div>
                <div v-if="selectedProgressSetId && progressView === 'student'" class="courses-search-wrap panel-search">
                  <svg class="courses-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <input v-model.trim="progressStudentSearch" type="search" class="courses-search-input" placeholder="Search students" aria-label="Search progress students" />
                </div>
              </div>

              <div v-if="selectedProgressSetId && progressView === 'student'" class="ep-split">
                <aside class="ep-student-panel">
                  <div class="ep-student-panel__header">
                    <h4 class="ep-student-panel__title">Students</h4>
                    <span class="ep-student-panel__count">{{ progressStudentsBySet(selectedProgressSetId).length }}</span>
                  </div>
                  <div class="ep-student-list">
                    <button
                      v-for="student in progressStudentsBySet(selectedProgressSetId)"
                      :key="student.email"
                      type="button"
                      class="ep-student-row"
                      :class="{ active: selectedProgressStudentEmail === student.email }"
                      @click="selectedProgressStudentEmail = student.email"
                    >
                      <div class="ep-student-row__avatar">{{ student.name.charAt(0).toUpperCase() }}</div>
                      <div class="ep-student-row__info">
                        <div class="ep-student-row__name">{{ student.name }}</div>
                        <div class="ep-student-row__email">{{ student.email }}</div>
                      </div>
                    </button>
                  </div>
                </aside>

                <div class="ep-results-panel">
                  <div v-if="!selectedProgressStudentEmail" class="ep-results-empty">
                    <div class="ep-results-empty__icon">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    </div>
                    <p class="ep-results-empty__title">Select a student</p>
                    <p class="ep-results-empty__sub">Pick someone from the list to view their exam scores and proctoring flags.</p>
                  </div>
                  <div v-else class="ep-results-header">
                    <div>
                      <h4 class="ep-results-header__title">{{ progressStudentsBySet(selectedProgressSetId).find(s => s.email === selectedProgressStudentEmail)?.name }}'s results</h4>
                      <p class="ep-results-header__sub">All assigned exams for this section</p>
                    </div>
                  </div>
                  <div v-if="selectedProgressStudentEmail" class="ep-table-scroll">
                  <table class="data-table ep-table ep-student-results-table">
                  <thead>
                    <tr>
                      <th>Exam</th>
                      <th>Status</th>
                      <th style="text-align:center">Score</th>
                      <th style="text-align:center">Integrity</th>
                      <th>Flags</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="row in selectedStudentProgressRows"
                      :key="`${row.exam_set_id}-${row.student_email}`"
                      :class="{ 'ep-row-terminated': row.terminated }"
                    >
                      <!-- Exam name -->
                      <td class="bold-td ep-exam-name">{{ formatDisplayTitle(row.exam_title) }}</td>

                      <!-- Status badge -->
                      <td>
                        <span class="status-badge" :class="submissionStatusClass(row)">
                          {{ submissionStatus(row) }}
                        </span>
                      </td>

                      <!-- Score -->
                      <td style="text-align:center">
                        <span class="ep-score" :class="{ 'ep-score--zero': !row.is_done && row.due_at && new Date() > new Date(row.due_at) }">
                          {{ row.is_done && row.score != null ? row.score : (row.due_at && new Date() > new Date(row.due_at) ? '0' : '—') }}
                        </span>
                      </td>

                      <!-- Integrity % -->
                      <td style="text-align:center">
                        <span
                          v-if="row.is_done && row.integrity_score != null"
                          class="ep-integrity"
                          :class="row.integrity_score < 50 ? 'ep-integrity--bad' : row.integrity_score < 80 ? 'ep-integrity--warn' : 'ep-integrity--good'"
                        >{{ row.integrity_score }}%</span>
                        <span v-else class="ep-dash">—</span>
                      </td>

                      <!-- Flags / proctoring summary -->
                      <td>
                        <div v-if="!row.is_done" class="ep-dash">—</div>
                        <div v-else-if="row.terminated || row.tab_switches > 0 || row.gaze_violation_count > 0 || row.gaze_no_face_count > 0 || row.gadget_detection_count > 0" class="ep-flags">
                          <span v-if="row.terminated" class="ep-flag ep-flag--critical">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 22h20z"/></svg>
                            Auto-terminated
                          </span>
                          <span v-if="row.tab_switches" class="ep-flag ep-flag--warn">{{ row.tab_switches }} tab{{ row.tab_switches !== 1 ? 's' : '' }}</span>
                          <span v-if="row.gaze_violation_count" class="ep-flag ep-flag--warn">{{ row.gaze_violation_count }} gaze</span>
                          <span v-if="row.gaze_no_face_count" class="ep-flag ep-flag--warn">{{ row.gaze_no_face_count }} hidden</span>
                          <span v-if="row.gadget_detection_count" class="ep-flag ep-flag--warn">{{ row.gadget_detection_count }} gadget{{ row.gadget_detection_count !== 1 ? 's' : '' }}</span>
                        </div>
                        <div v-else class="ep-clean">
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                          Clean
                        </div>
                      </td>

                      <!-- Report button -->
                      <td>
                        <button
                          v-if="row.is_done"
                          type="button"
                          class="ep-report-btn"
                          :class="{ 'ep-report-btn--grade': row.pending_subjective_count > 0 }"
                          @click="openIntegrityReport(row)"
                        >
                          {{ row.pending_subjective_count > 0 ? `Grade ${row.pending_subjective_count}` : 'Review' }}
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                        </button>
                        <span v-else class="ep-dash">—</span>
                      </td>
                    </tr>
                    <tr v-if="selectedStudentProgressRows.length === 0">
                      <td colspan="6" class="ep-table-empty">No exam data for this student.</td>
                    </tr>
                  </tbody>
                </table>
                </div>
                </div>
              </div>

              <div v-if="selectedProgressSetId && progressView === 'exam'" class="ep-split">
                <aside class="ep-student-panel">
                  <div class="ep-student-panel__header">
                    <h4 class="ep-student-panel__title">Exams / quizzes</h4>
                    <span class="ep-student-panel__count">{{ progressExamsForSelectedSet.length }}</span>
                  </div>
                  <div class="ep-student-list">
                    <button
                      v-for="exam in progressExamsForSelectedSet"
                      :key="exam.id"
                      type="button"
                      class="ep-student-row"
                      :class="{ active: selectedProgressExamId === exam.id }"
                      @click="selectedProgressExamId = exam.id"
                    >
                      <div class="ep-student-row__avatar">{{ formatDisplayTitle(exam.title).charAt(0).toUpperCase() }}</div>
                      <div class="ep-student-row__info">
                        <div class="ep-student-row__name">{{ formatDisplayTitle(exam.title) }}</div>
                        <div class="ep-student-row__email">{{ exam.studentCount }} {{ exam.studentCount === 1 ? 'student' : 'students' }}</div>
                      </div>
                    </button>
                  </div>
                </aside>

                <div class="ep-results-panel ep-assessment-panel">
                  <div class="ep-results-header">
                    <h4 class="ep-results-header__title">{{ selectedProgressExamTitle }}</h4>
                    <p class="ep-results-header__sub">Student results for this exam or quiz</p>
                  </div>
                  <div class="ep-table-scroll">
                  <table class="data-table ep-table ep-assessment-table">
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Status</th>
                        <th style="text-align:center">Actual score</th>
                        <th style="text-align:center">Integrity score</th>
                        <th>Flags</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="row in sortedSelectedSetExamRows"
                        :key="`${row.exam_set_id}-${row.student_email}`"
                        :class="{ 'ep-row-terminated': row.terminated }"
                      >
                        <td>
                          <div class="student-row">
                            <div class="student-avatar">{{ progressStudentName(row.student_email).charAt(0).toUpperCase() }}</div>
                            <div class="ep-student-row__info">
                              <div class="ep-student-row__name">{{ progressStudentName(row.student_email) }}</div>
                              <div class="ep-student-row__email">{{ row.student_email }}</div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span class="status-badge" :class="submissionStatusClass(row)">
                            {{ submissionStatus(row) }}
                          </span>
                        </td>
                        <td style="text-align:center">
                          <span class="ep-score" :class="{ 'ep-score--zero': !row.is_done && row.due_at && new Date() > new Date(row.due_at) }">
                            {{ row.is_done && row.score != null ? row.score : (row.due_at && new Date() > new Date(row.due_at) ? '0' : '—') }}
                          </span>
                        </td>
                        <td style="text-align:center">
                          <span
                            v-if="row.is_done && row.integrity_score != null"
                            class="ep-integrity"
                            :class="row.integrity_score < 50 ? 'ep-integrity--bad' : row.integrity_score < 80 ? 'ep-integrity--warn' : 'ep-integrity--good'"
                          >{{ row.integrity_score }}%</span>
                          <span v-else class="ep-dash">—</span>
                        </td>
                        <td>
                          <div v-if="!row.is_done" class="ep-dash">—</div>
                          <div v-else-if="row.terminated || row.tab_switches > 0 || row.gaze_violation_count > 0 || row.gaze_no_face_count > 0 || row.gadget_detection_count > 0" class="ep-flags">
                            <span v-if="row.terminated" class="ep-flag ep-flag--critical">Auto-terminated</span>
                            <span v-if="row.tab_switches" class="ep-flag ep-flag--warn">{{ row.tab_switches }} tab{{ row.tab_switches !== 1 ? 's' : '' }}</span>
                            <span v-if="row.gaze_violation_count" class="ep-flag ep-flag--warn">{{ row.gaze_violation_count }} gaze</span>
                            <span v-if="row.gaze_no_face_count" class="ep-flag ep-flag--warn">{{ row.gaze_no_face_count }} hidden</span>
                            <span v-if="row.gadget_detection_count" class="ep-flag ep-flag--warn">{{ row.gadget_detection_count }} gadget{{ row.gadget_detection_count !== 1 ? 's' : '' }}</span>
                          </div>
                          <div v-else class="ep-clean">
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                            Clean
                          </div>
                        </td>
                        <td>
                          <button
                            v-if="row.is_done"
                            type="button"
                            class="ep-report-btn"
                            :class="{ 'ep-report-btn--grade': row.pending_subjective_count > 0 }"
                            @click="openIntegrityReport(row)"
                          >
                            {{ row.pending_subjective_count > 0 ? `Grade ${row.pending_subjective_count}` : 'Review' }}
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                          </button>
                          <span v-else class="ep-dash">—</span>
                        </td>
                      </tr>
                      <tr v-if="sortedSelectedSetExamRows.length === 0">
                        <td colspan="6" class="ep-table-empty">No student results are available for this exam or quiz.</td>
                      </tr>
                    </tbody>
                  </table>
                  </div>
                </div>
              </div>
            </template>
            <p v-if="examProgressError" class="error">{{ examProgressError }}</p>
          </div>
          </div>

            </div><!-- /course-tab-panel -->
          </div><!-- /course-tabs-card -->
          </div><!-- /course-workspace -->
        </template>

        <!-- GLOBAL MESSAGES -->
        <NoticeModal :model-value="Boolean(message)" :title="messageTitle" :message="message" @close="message = ''" />
        <p v-if="error" class="error global">{{ error }}</p>

      </main>

      <!-- RIGHT PANEL REMOVED FOR MORE SPACE -->

    </div>

    <!-- MANAGE QUESTIONS EDITOR -->
    <div v-if="managingExam" class="qe-overlay">
      <div class="qe-shell">
        <header class="qe-header">
          <div class="qe-header__copy">
            <button type="button" class="cw-back-btn cw-back-btn--light" @click="closeManageQuestions">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
              Back
            </button>
            <div class="cw-title-row">
              <span class="exam-item__badge" :class="examIsFinal ? 'exam-item__badge--pub' : 'exam-item__badge--draft'">{{ examIsFinal ? 'Published' : 'Draft' }}</span>
              <h1>{{ managingExam.title }}</h1>
            </div>
            <p class="header-sub">{{ examQuestions.length }} {{ examQuestions.length === 1 ? 'question' : 'questions' }} selected from the course bank. Publish when the set is ready.</p>
          </div>
          <button type="button" class="ghost-btn" @click="closeManageQuestions">Close</button>
        </header>

        <div class="qe-grid">
          
          <!-- LEFT SIDE: EXISTING QUESTIONS -->
          <div class="qe-col">
            <h2 style="font-size: 1.4rem; font-weight: 700; margin-bottom: 1.5rem; color: #334155;">Exam preview</h2>
            <div class="taking-questions">
            <template v-if="questionsLoading">
              <SkeletonLoader type="text" width="60%" height="2rem" />
              <SkeletonLoader type="card" height="200px" style="margin-top:1rem;" />
            </template>
            <EmptyState 
              v-else-if="examQuestions.length === 0" 
              style="margin-top:2rem;" 
              title="Empty Exam" 
              description="Select questions from the course bank to assemble this exam."
            />
            <template v-else>
              <div class="q-list">
              <div v-for="(q, idx) in examQuestions" :key="q.id" class="q-card bank-exam-preview" style="margin-bottom: 0.65rem;">
                <div class="q-header" style="justify-content: flex-start; gap: 0.75rem;">
                  <strong style="color: #0f172a;">Q{{ idx + 1 }}.</strong>
                  <span class="bank-item__type">{{ questionTypeLabel(q.question_type) }}</span>
                </div>
                <div class="bank-exam-preview__body">
                  <p class="q-text">{{ q.question_text }}</p>
                  <details class="bank-item__details">
                    <summary>Show answer</summary>
                    <ul v-if="q.choices?.length"><li v-for="choice in q.choices" :key="choice">{{ choice }}</li></ul>
                    <span>{{ q.correct_answer || 'Manual grading' }}</span>
                  </details>
                </div>
                <button v-if="!examIsFinal" type="button" class="bank-item__delete" @click="deleteExamQuestion(q.id)">Remove</button>
            </div>
            </div>
            </template>
            </div>
            
            <!-- PROCTORING SETTINGS (PREMIUM UI) -->
            <div style="margin-top: 2rem; background: #ffffff; border: 1px solid #e8e6f5; border-radius: 12px; box-shadow: 0 4px 20px rgba(74,69,124,0.06); overflow: hidden;">
              <div style="background: linear-gradient(135deg, #f8fafc, #f1f5f9); padding: 1.25rem 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;">
                <div style="flex: 1;">
                  <h4 style="font-size: 1.15rem; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 0.5rem; font-weight: 700;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4a457c" stroke-width="2.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3" stroke="#4a457c" stroke-width="2.5"/></svg>
                    Essay Proctoring Restrictions
                  </h4>
                  <p style="font-size: 0.85rem; color: #64748b; margin: 0.25rem 0 0 0;">
                    {{ examRequiresAllRestrictions
                      ? 'Add at least one essay question to customize these settings.'
                      : 'These choices apply only while students are answering essay questions. All restrictions remain active for earlier objective questions.' }}
                  </p>
                </div>
                <span style="flex-shrink: 0; white-space: nowrap; background: #e0e7ff; color: #4338ca; font-size: 0.7rem; font-weight: 800; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px;">
                  {{ restrictionsSaving ? 'Saving…' : (examRequiresAllRestrictions ? 'Required' : 'Essay section') }}
                </span>
              </div>
              
              <div style="padding: 1.5rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.25rem;">
                
                <!-- Toggle 1: Above -->
                <label class="premium-toggle-card" :class="{ 'premium-toggle-card--locked': examIsFinal || examRequiresAllRestrictions }">
                  <div class="ptc-icon" style="background: #e0f2fe; color: #0369a1;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg></div>
                  <div class="ptc-info">
                    <span class="ptc-title">Looking Above</span>
                    <span class="ptc-desc">Detect upward glances</span>
                  </div>
                  <div class="premium-switch">
                    <input v-model="examRestrictions.gaze_above" type="checkbox" :disabled="examIsFinal || examRequiresAllRestrictions || restrictionsSaving" @change="saveExamRestrictions" />
                    <span class="premium-slider"></span>
                  </div>
                </label>

                <!-- Toggle 2: Below -->
                <label class="premium-toggle-card" :class="{ 'premium-toggle-card--locked': examIsFinal || examRequiresAllRestrictions }">
                  <div class="ptc-icon" style="background: #fce7f3; color: #be185d;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg></div>
                  <div class="ptc-info">
                    <span class="ptc-title">Looking Below</span>
                    <span class="ptc-desc">Detect downward focus</span>
                  </div>
                  <div class="premium-switch">
                    <input v-model="examRestrictions.gaze_below" type="checkbox" :disabled="examIsFinal || examRequiresAllRestrictions || restrictionsSaving" @change="saveExamRestrictions" />
                    <span class="premium-slider"></span>
                  </div>
                </label>

                <!-- Toggle 3: Left -->
                <label class="premium-toggle-card" :class="{ 'premium-toggle-card--locked': examIsFinal || examRequiresAllRestrictions }">
                  <div class="ptc-icon" style="background: #fef3c7; color: #b45309;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg></div>
                  <div class="ptc-info">
                    <span class="ptc-title">Looking Left</span>
                    <span class="ptc-desc">Detect leftward off-screen</span>
                  </div>
                  <div class="premium-switch">
                    <input v-model="examRestrictions.gaze_left" type="checkbox" :disabled="examIsFinal || examRequiresAllRestrictions || restrictionsSaving" @change="saveExamRestrictions" />
                    <span class="premium-slider"></span>
                  </div>
                </label>

                <!-- Toggle 4: Right -->
                <label class="premium-toggle-card" :class="{ 'premium-toggle-card--locked': examIsFinal || examRequiresAllRestrictions }">
                  <div class="ptc-icon" style="background: #dcfce7; color: #15803d;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg></div>
                  <div class="ptc-info">
                    <span class="ptc-title">Looking Right</span>
                    <span class="ptc-desc">Detect rightward off-screen</span>
                  </div>
                  <div class="premium-switch">
                    <input v-model="examRestrictions.gaze_right" type="checkbox" :disabled="examIsFinal || examRequiresAllRestrictions || restrictionsSaving" @change="saveExamRestrictions" />
                    <span class="premium-slider"></span>
                  </div>
                </label>

                <!-- Toggle 5: Prohibited devices -->
                <label class="premium-toggle-card" :class="{ 'premium-toggle-card--locked': examIsFinal || examRequiresAllRestrictions }">
                  <div class="ptc-icon" style="background: #fee2e2; color: #b91c1c;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="9" y1="18" x2="15" y2="18"/></svg></div>
                  <div class="ptc-info">
                    <span class="ptc-title">Gadget Detection</span>
                    <span class="ptc-desc">Detect phones and laptops</span>
                  </div>
                  <div class="premium-switch">
                    <input v-model="examRestrictions.gadgets" type="checkbox" :disabled="examIsFinal || examRequiresAllRestrictions || restrictionsSaving" @change="saveExamRestrictions" />
                    <span class="premium-slider"></span>
                  </div>
                </label>

              </div>
            </div>

            <div style="margin-top: 3rem; padding-top: 2rem; border-top: 2px dashed #e2e8f0;">
              <h4 style="font-size: 1.2rem; color: #0f172a; margin-bottom: 0.5rem;">Ready to publish?</h4>
              <p class="muted" style="text-align: left; margin-top: 0; margin-bottom: 1rem;">Once finalized, you can no longer alter questions, and students will be able to take the exam.</p>
              <button class="primary-btn" style="width: 100%; font-size: 1.1rem; padding: 0.8rem;" :style="{ background: examIsFinal ? '#64748b' : (examQuestions.length === 0 ? '#9ca3af' : '#059669'), cursor: (examIsFinal || examQuestions.length === 0) ? 'not-allowed' : 'pointer' }" type="button" @click="finalizeExam" :disabled="questionsLoading || examIsFinal || examQuestions.length === 0">
                {{ examIsFinal ? 'Exam is Finalized & Locked' : (examQuestions.length === 0 ? 'Add at least 1 question to publish' : 'Submit & Finalize Exam') }}
              </button>
            </div>
          </div>
          
          <!-- RIGHT SIDE: CHOOSE QUESTIONS FROM COURSE BANK -->
          <div v-if="!examIsFinal" class="qe-col qe-col--stack bank-select-panel">
            <div class="bank-editor-card draft-bank-card">
              <div class="bank-panel-heading"><span class="bank-panel-heading__icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 5h16v14H4z"/><path d="M8 9h8M8 13h8"/></svg></span><div><span class="bank-eyebrow">COURSE QUESTION BANK</span><h2>Available questions</h2></div></div>
              <p>Open a batch and choose the questions for this exam. Already added questions remain marked below.</p>
              <div class="draft-bank-summary"><span><strong>{{ bankBatches.length }}</strong> batches</span><span><strong>{{ availableBankQuestions.length }}</strong> available</span><span><strong>{{ selectedBankQuestionIds.length }}</strong> selected</span></div>
              <div class="bank-filter-row">
                <input v-model.trim="bankSelectSearch" type="search" class="create-panel__input" placeholder="Search bank questions" aria-label="Search bank questions for exam" />
                <select v-model="bankSelectType" class="create-panel__input" aria-label="Filter selectable question type">
                  <option value="all">All types</option>
                  <option value="multiple_choice">Multiple choice</option>
                  <option value="identification">Identification</option>
                  <option value="enumeration">Enumeration</option>
                  <option value="essay">Essay</option>
                </select>
              </div>
              <p v-if="bankLoading" class="bank-help">Loading question bank…</p>
              <div v-else-if="!bankQuestions.length" class="draft-bank-empty"><strong>No questions in this course bank yet</strong><p>Create or import a batch in the Question Bank page, then return here to assemble this exam.</p><button type="button" class="ghost-btn" @click="closeManageQuestions(); activeCourseTab = 'question-bank'">Open Question Bank</button></div>
              <p v-else-if="!selectableBankBatches.length" class="bank-help">No questions match this search.</p>
              <div v-else class="bank-select-list">
                <details v-for="(batch, index) in selectableBankBatches" :key="batch.id" class="bank-batch" :open="selectableBankBatches.length === 1">
                  <summary><span class="bank-batch__index">{{ String(index + 1).padStart(2, '0') }}</span><strong>{{ batch.name }}</strong><span>{{ batch.questions.length }} questions</span></summary>
                  <label v-for="item in batch.questions" :key="item.id" class="bank-select-item" :class="{ 'bank-select-item--added': examBankItemIds.has(item.id) }">
                    <input v-model="selectedBankQuestionIds" type="checkbox" :value="item.id" :disabled="examBankItemIds.has(item.id) || bankSaving" />
                    <span><small>{{ questionTypeLabel(item.question_type) }}</small><strong>{{ item.question_text }}</strong></span>
                    <em v-if="examBankItemIds.has(item.id)">Added</em>
                  </label>
                </details>
              </div>
              <div class="bank-select-actions">
                <span>{{ selectedBankQuestionIds.length ? `${selectedBankQuestionIds.length} ready to add` : 'Select questions from a batch' }}</span>
                <button type="button" class="primary-btn" :disabled="bankSaving || !selectedBankQuestionIds.length" @click="addSelectedBankQuestions">
                  {{ bankSaving ? 'Adding…' : `Add ${selectedBankQuestionIds.length} to exam` }}
                </button>
              </div>
              <button type="button" class="bank-text-button draft-bank-link" @click="closeManageQuestions(); activeCourseTab = 'question-bank'">Open Question Bank to create or import questions →</button>
            </div>

          </div>

        </div>
      </div>
    </div>

    <!-- EXAM STATS MODAL -->
    <transition name="stats-fade">
      <div v-if="statsExam" class="stats-backdrop" @click.self="closeExamStats" role="dialog" aria-modal="true" aria-labelledby="stats-modal-title">
        <div class="stats-shell">
          <!-- Header -->
          <header class="stats-header">
            <div class="stats-header-content">
              <span class="stats-eyebrow">Exam overview</span>
              <h2 id="stats-modal-title" class="stats-title">{{ formatDisplayTitle(statsExam.title) }}</h2>
              <p class="stats-course-label">{{ formatDisplayTitle(`${statsExam.subject_code || ''} ${statsExam.subject_name || ''}`.trim()) }}</p>
            </div>
            <button type="button" class="stats-close-btn" @click="closeExamStats" aria-label="Close">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </header>

          <!-- Summary pills -->
          <div v-if="!statsLoading && examStatsSets.length > 0" class="stats-summary-bar">
            <div class="stats-summary-pill">
              <span class="ssp-num">{{ examStatsSets.reduce((a,s)=>a+Number(s.total||0),0) }}</span>
              <span class="ssp-lbl">Examinees</span>
            </div>
            <div class="stats-summary-pill stats-summary-pill--green">
              <span class="ssp-num">{{ examStatsSets.reduce((a,s)=>a+Number(s.done||0),0) }}</span>
              <span class="ssp-lbl">Completed</span>
            </div>
            <div class="stats-summary-pill stats-summary-pill--amber">
              <span class="ssp-num">{{ examStatsSets.reduce((a,s)=>a+Number(s.total||0),0) - examStatsSets.reduce((a,s)=>a+Number(s.done||0),0) }}</span>
              <span class="ssp-lbl">Not completed</span>
            </div>
          </div>

          <!-- Body -->
          <div class="stats-body">
            <div v-if="statsLoading" class="stats-loading-state" role="status" aria-label="Loading statistics">
              <SkeletonLoader type="text" width="35%" height="1.5rem" />
              <SkeletonLoader type="row" v-for="i in 4" :key="i" />
              <span class="visually-hidden">Loading statistics</span>
            </div>
            <!-- Live examinees stay visible even when no one has started yet. -->
            <div v-else class="stats-examinees-section">
              <div class="stats-examinees-heading">
                <div>
                  <span class="stats-live-label"><span class="stats-live-dot"></span> Live view</span>
                  <h3 class="stats-examinees-title">Examinees</h3>
                </div>
                <span class="stats-refresh-note">Updates every 5 seconds</span>
              </div>
              <div class="stats-table-wrapper">
                <table class="stats-table">
                  <thead>
                    <tr>
                      <th>Examinee</th>
                      <th>Set</th>
                      <th>Status</th>
                      <th>Activity</th>
                      <th class="stats-center">Live view</th>
                      <th class="stats-center">Report</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(ex, i) in examStatsExaminees" :key="i">
                      <td>
                        <div class="stats-ex-name">{{ ex.name }}</div>
                        <div class="stats-ex-email">{{ ex.email }}</div>
                      </td>
                      <td>{{ ex.set_name }}</td>
                      <td>
                        <span class="stats-badge" :class="{
                          'stats-badge--green': getExamineeReportStatus(ex)==='Done',
                          'stats-badge--blue': getExamineeReportStatus(ex)==='Ongoing',
                          'stats-badge--red': getExamineeReportStatus(ex)==='Terminated',
                          'stats-badge--orange': getExamineeReportStatus(ex)==='Not Taken',
                          'stats-badge--amber': getExamineeReportStatus(ex)==='Pending'
                        }">
                          {{ getExamineeReportStatus(ex) }}
                        </span>
                      </td>
                      <td>
                        <div class="stats-activity">
                          <span :class="{'stats-warn-text': ex.tab_switches > 0}">{{ ex.tab_switches }} tab switches</span>
                          <span :class="{'stats-warn-text': ex.gaze_violation_count + ex.gaze_no_face_count > 0}" :title="`Gaze away: ${ex.gaze_violation_count} | No face: ${ex.gaze_no_face_count}`">{{ ex.gaze_violation_count + ex.gaze_no_face_count }} gaze alerts</span>
                        </div>
                      </td>
                      <td class="stats-center">
                        <div class="stats-snapshot-wrapper">
                          <img v-if="ex.snapshot_display_url" :key="ex.snapshot_display_url" :src="ex.snapshot_display_url" class="stats-snapshot-img" alt="Latest webcam snapshot" />
                          <div v-else class="stats-snapshot-placeholder">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                          </div>
                        </div>
                      </td>
                      <td class="stats-center">
                        <button
                          v-if="getExamineeReportStatus(ex) !== 'Not Started'"
                          type="button"
                          class="stats-report-btn"
                          @click="openIntegrityReport({ exam_set_id: statsExam.id, subject_id: statsExam.subject_id, student_email: ex.email, score: ex.score ?? null })"
                        >View Report →</button>
                        <span v-else style="color: #d1d5db; font-size: 0.75rem;">—</span>
                      </td>
                    </tr>
                    <tr v-if="examStatsExaminees.length === 0"><td colspan="6" class="stats-table-empty">No examinees are assigned yet.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </transition>

    <!-- PROCTORING / INTEGRITY REPORT premium dark drawer -->
    <transition name="ir-slide">
      <div v-if="integrityReportOpen" class="ir-backdrop" @click.self="integrityReportOpen = false" role="dialog" aria-modal="true" aria-labelledby="ir-title">
        <div class="ir-drawer">

          <!-- Header -->
          <header class="ir-drawer-header">
            <div class="ir-dh-glow"></div>
            <div class="ir-dh-glow ir-dh-glow--r"></div>
            <div class="ir-dh-content">
              <span class="ir-dh-eyebrow">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                Submission Review
              </span>
              <h2 id="ir-title" class="ir-dh-title">{{ formatDisplayTitle(integrityReportData.exam_title) || 'Exam' }}</h2>
              <div class="ir-dh-meta">
                <span class="ir-dh-email">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
                  {{ integrityReportData.student_email || integrityReportData._student_email }}
                </span>
                <span v-if="integrityReportData.attempt_number" class="ir-dh-attempt">Attempt {{ integrityReportData.attempt_number }}</span>
              </div>
            </div>
            <button type="button" class="ir-dh-close" @click="integrityReportOpen = false" aria-label="Close">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </header>

          <!-- Loading -->
          <div v-if="integrityReportLoading" class="ir-state">
            <div class="ir-spinner" aria-hidden="true"></div>
            <p>Loading report...</p>
          </div>

          <!-- Error -->
          <div v-else-if="integrityReportError" class="ir-state ir-state-error">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <p>{{ integrityReportError }}</p>
          </div>

          <!-- Main content -->
          <template v-else>

            <!-- METRIC HERO -->
            <section class="ir-hero">

              <!-- Left: integrity ring -->
              <div
                class="ir-dial"
                :class="integrityScoreTone(integrityReportData.report?.integrity_score)"
              >
                <svg class="ir-dial-svg" viewBox="0 0 100 100">
                  <circle class="ir-dial-track" cx="50" cy="50" r="40" fill="none" stroke-width="7"/>
                  <circle
                    class="ir-dial-fill"
                    cx="50" cy="50" r="40" fill="none" stroke-width="7"
                    stroke-dasharray="251.2"
                    :stroke-dashoffset="251.2 - (251.2 * (integrityReportData.report?.integrity_score ?? 0) / 100)"
                    stroke-linecap="round"
                    transform="rotate(-90 50 50)"
                  />
                </svg>
                <div class="ir-dial-inner">
                  <span class="ir-dial-val">{{ integrityReportData.report?.integrity_score ?? '—' }}</span>
                  <span class="ir-dial-unit" v-if="integrityReportData.report?.integrity_score != null">%</span>
                  <span class="ir-dial-lbl">Integrity</span>
                </div>
              </div>

              <!-- Right panel -->
              <div class="ir-hero-right">

                <!-- Top row: score + status -->
                <div class="ir-top-row">
                  <div class="ir-score-block">
                    <span class="ir-score-num">{{ integrityReportData.submission?.score != null ? integrityReportData.submission.score : (integrityReportData._student_score ?? '—') }}</span>
                    <span class="ir-score-lbl">Exam Score</span>
                  </div>
                  <div class="ir-top-divider"></div>
                  <div class="ir-status-block">
                    <span v-if="integrityReportData.submission?.terminated" class="ir-status-chip ir-chip-terminated">
                      <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 22h20z"/></svg>
                      Auto-terminated
                    </span>
                    <span v-else-if="integrityReportData.submission?.is_done" class="ir-status-chip ir-chip-done">
                      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                      Completed
                    </span>
                    <span v-else class="ir-status-chip ir-chip-pending">In Progress</span>
                  </div>
                </div>

                <!-- Bottom row: 4 metrics with dividers -->
                <div class="ir-metrics-row">
                  <div class="ir-metric">
                    <span class="ir-metric-num">{{ integrityReportData.report?.tab_switch_count ?? 0 }}</span>
                    <span class="ir-metric-lbl">Tab Switches</span>
                  </div>
                  <div class="ir-metric-sep"></div>
                  <div class="ir-metric" :class="(integrityReportData.report?.gaze_violation_count ?? 0) > 0 ? 'ir-metric-warn' : ''">
                    <span class="ir-metric-num">{{ integrityReportData.report?.gaze_violation_count ?? 0 }}</span>
                    <span class="ir-metric-lbl">Gaze Away</span>
                  </div>
                  <div class="ir-metric-sep"></div>
                  <div class="ir-metric" :class="(integrityReportData.report?.gaze_no_face_count ?? 0) > 0 ? 'ir-metric-danger' : ''">
                    <span class="ir-metric-num">{{ integrityReportData.report?.gaze_no_face_count ?? 0 }}</span>
                    <span class="ir-metric-lbl">Face Hidden</span>
                  </div>
                  <div class="ir-metric-sep"></div>
                  <div class="ir-metric">
                    <span class="ir-metric-num">{{ evidenceImages.length + snapshotImages.length }}</span>
                    <span class="ir-metric-lbl">Images shown</span>
                  </div>
                </div>

              </div>
            </section>

            <!-- DETAIL TABS -->
            <div class="ir-tab-bar">
              <button class="ir-tab-btn" :class="{ 'ir-tab-btn--active': activeIrTab === 'answers' }" @click="activeIrTab = 'answers'">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                Answers &amp; grading
                <span v-if="pendingSubjectiveAnswers.length" class="ir-tab-count">{{ pendingSubjectiveAnswers.length }}</span>
                <span v-else-if="(integrityReportData.subjective_answers || []).length" class="ir-tab-count ir-tab-count--done">✓</span>
              </button>
              <button class="ir-tab-btn" :class="{ 'ir-tab-btn--active': activeIrTab === 'log' }" @click="activeIrTab = 'log'">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                Action Log
                <span class="ir-tab-count" v-if="(integrityReportData.events || []).length">{{ (integrityReportData.events || []).length }}</span>
              </button>
              <button class="ir-tab-btn" :class="{ 'ir-tab-btn--active': activeIrTab === 'gallery' }" @click="activeIrTab = 'gallery'">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                Evidence
                <span class="ir-tab-count" v-if="evidenceImages.length">{{ evidenceImages.length }}</span>
              </button>
              <button class="ir-tab-btn" :class="{ 'ir-tab-btn--active': activeIrTab === 'snapshots' }" @click="activeIrTab = 'snapshots'">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
                Snapshots
                <span class="ir-tab-count" v-if="snapshotImages.length">{{ snapshotImages.length }}</span>
              </button>
            </div>

            <!-- TAB: SUBJECTIVE ANSWERS -->
            <div v-if="activeIrTab === 'answers'" class="ir-tab-panel">
              <div v-if="(integrityReportData.subjective_answers || []).length" class="ir-grading-list">
                <div class="ir-grading-summary" :class="integrityReportData.manual_grading_complete ? 'ir-grading-summary--done' : ''">
                  <div>
                    <strong>{{ integrityReportData.manual_grading_complete ? 'Grading complete' : 'Manual grading required' }}</strong>
                    <p>{{ integrityReportData.manual_grading_complete ? 'Every response has been checked.' : 'Score the remaining responses, then save the grades.' }}</p>
                  </div>
                  <span>{{ gradedSubjectiveCount }} / {{ integrityReportData.subjective_answers.length }} graded</span>
                </div>
                <button v-if="gradedSubjectiveCount" type="button" class="ir-review-checked" @click="reviewCheckedAnswers = !reviewCheckedAnswers">
                  {{ reviewCheckedAnswers ? 'Show unchecked answers' : `Review checked answers (${gradedSubjectiveCount})` }}
                </button>
                <div v-if="!visibleSubjectiveAnswers.length" class="ir-checked-empty">
                  <span class="ir-checked-empty-icon" aria-hidden="true">✓</span>
                  <strong>All answers checked</strong>
                  <p>The answer and grading fields are clear. Use Review checked answers if you need to change a score.</p>
                </div>
                <article v-for="answer in visibleSubjectiveAnswers" :key="answer.answer_id" class="ir-answer-card">
                  <div class="ir-answer-heading">
                    <span class="ir-answer-number">Question {{ answer.order }}</span>
                    <label class="ir-points-field">
                      <span>Score</span>
                      <input
                        v-model="answer._grade"
                        type="number"
                        min="0"
                        :max="answer.max_points"
                        step="0.25"
                        :aria-label="`Score for question ${answer.order}`"
                      />
                      <b>/ {{ answer.max_points }}</b>
                    </label>
                  </div>
                  <h4>{{ answer.question_text }}</h4>
                  <div class="ir-student-answer">
                    <span>Student answer</span>
                    <p>{{ answer.answer_text || 'No answer provided.' }}</p>
                  </div>
                </article>
                <div v-if="visibleSubjectiveAnswers.length" class="ir-grading-actions">
                  <p v-if="gradingError" class="ir-grading-error">{{ gradingError }}</p>
                  <button type="button" class="primary-btn" :disabled="gradingSaving" @click="saveSubjectiveGrades">
                    {{ gradingSaving ? 'Saving…' : 'Save grades' }}
                  </button>
                </div>
              </div>
              <div v-else class="ir-empty">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                <p>This exam has no subjective answers to grade.</p>
              </div>
            </div>

            <NoticeModal :model-value="Boolean(gradingMessage)" title="Grades saved" :message="gradingMessage" @close="gradingMessage = ''" />

            <!-- TAB: ACTION LOG -->
            <div v-if="activeIrTab === 'log'" class="ir-tab-panel">
              <div class="ir-log-list">
                <div
                  v-for="ev in integrityReportData.events || []"
                  :key="ev.id"
                  class="ir-log-row"
                  :class="{
                    'ir-log--critical': String(ev.severity).toLowerCase() === 'critical',
                    'ir-log--warning':  String(ev.severity).toLowerCase() === 'warning',
                  }"
                >
                  <div class="ir-log-bar"></div>
                  <div class="ir-log-icon">
                    <svg v-if="String(ev.severity).toLowerCase() === 'critical'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2L2 22h20z"/></svg>
                    <svg v-else-if="String(ev.severity).toLowerCase() === 'warning'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                  </div>
                  <div class="ir-log-body">
                    <div class="ir-log-top">
                      <span class="ir-log-type">{{ formatEventType(ev.event_type) }}</span>
                      <span class="ir-sev-badge" :class="severityClass(ev.severity)">{{ ev.severity }}</span>
                      <span class="ir-log-time">{{ formatReportTime(ev.created_at) }}</span>
                    </div>
                    <p class="ir-log-msg">{{ ev.message || ev.source || '—' }}</p>
                  </div>
                </div>
                <div v-if="!(integrityReportData.events || []).length" class="ir-empty">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
                  <p>No events recorded for this attempt.</p>
                </div>
              </div>
            </div>

            <!-- TAB: EVIDENCE GALLERY -->
            <div v-if="activeIrTab === 'gallery'" class="ir-tab-panel">
              <div v-if="evidenceImages.length" class="ir-gallery-grid">
                <a
                  v-for="shot in evidenceImages"
                  :key="shot.id"
                  class="ir-thumb"
                  :href="shot.image_url"
                  target="_blank"
                  rel="noopener"
                >
                  <div class="ir-thumb-img-wrap">
                    <img v-if="shot.image_url" :src="shot.image_url" :alt="evidenceDescription(shot)" loading="lazy" @error="onEvidenceImageError" />
                    <div v-else class="ir-thumb-missing">No image</div>
                    <div class="ir-thumb-overlay">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    </div>
                  </div>
                  <div class="ir-thumb-cap">
                    <span class="ir-thumb-badge">{{ evidenceCategory(shot) }}</span>
                    <span class="ir-thumb-caption">{{ evidenceDescription(shot) }}</span>
                    <time class="ir-thumb-time" :datetime="shot.created_at">{{ formatReportTime(shot.created_at) }}</time>
                  </div>
                </a>
              </div>
              <div v-else class="ir-empty">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                <p>No violation evidence captures stored for this attempt.</p>
              </div>
            </div>

            <!-- TAB: SCHEDULED SNAPSHOTS -->
            <div v-if="activeIrTab === 'snapshots'" class="ir-tab-panel">
              <div v-if="snapshotImages.length" class="ir-gallery-grid">
                <a
                  v-for="shot in snapshotImages"
                  :key="shot.id"
                  class="ir-thumb"
                  :href="shot.image_url"
                  target="_blank"
                  rel="noopener"
                >
                  <div class="ir-thumb-img-wrap">
                    <img v-if="shot.image_url" :src="shot.image_url" :alt="evidenceDescription(shot)" loading="lazy" @error="onEvidenceImageError" />
                    <div v-else class="ir-thumb-missing">No image</div>
                    <div class="ir-thumb-overlay">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    </div>
                  </div>
                  <div class="ir-thumb-cap">
                    <span class="ir-thumb-badge">{{ evidenceCategory(shot) }}</span>
                    <span class="ir-thumb-caption">{{ evidenceDescription(shot) }}</span>
                    <time class="ir-thumb-time" :datetime="shot.created_at">{{ formatReportTime(shot.created_at) }}</time>
                  </div>
                </a>
              </div>
              <div v-else class="ir-empty">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
                <p>No scheduled snapshots available for this attempt.</p>
              </div>
            </div>

          </template>
        </div>
      </div>
    </transition>

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
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import ConfirmModal from "@/components/ConfirmModal.vue";
import ExamRow from "@/components/ExamRow.vue";
import CourseCard from "@/components/CourseCard.vue";
import SetRow from "@/components/SetRow.vue";
import SettingsPanel from "@/components/SettingsPanel.vue";
import SkeletonLoader from "@/components/SkeletonLoader.vue";
import EmptyState from "@/components/EmptyState.vue";
import UserProfileSettings from "@/components/UserProfileSettings.vue";
import NoticeModal from "@/components/NoticeModal.vue";
import { evidenceCategory, evidenceDescription, groupExamEvidence } from "@/utils/examEvidence.js";
import { calendarDayKey, calendarMonthDays } from "@/utils/examCalendar.js";
import {
  compareExamsNewestFirst,
  examAnchorTimestamp,
  examTimelineDisplayAt,
  formatExamTimelineTime,
  instructorExamOnDashboard,
  localDatetimeInputToApi,
} from "@/utils/examTimeline.js";

const router = useRouter();
const route = useRoute();

const currentUserStr = ref(localStorage.getItem('user') || '{}');
const currentUser = computed(() => {
  try { return JSON.parse(currentUserStr.value); }
  catch { return {}; }
});

function onSettingsUpdated(updatedUser) {
  if (updatedUser) {
    localStorage.setItem("user", JSON.stringify(updatedUser));
    currentUserStr.value = JSON.stringify(updatedUser);
  }
}
const instructorName = computed(() => {
  const n = String(currentUser.value?.name || '').trim();
  if (n) return n;
  const e = String(currentUser.value?.email || '').trim();
  return e.includes('@') ? e.split('@')[0] : 'Instructor';
});
const instructorEmail = computed(() => {
  const e = String(currentUser.value?.email || '').trim();
  return e.toLowerCase();
});

const profileLoading = ref(false);
const profileError = ref("");
const profileSuccess = ref("");

async function handleProfileUpdate(formData) {
  profileLoading.value = true;
  profileError.value = "";
  profileSuccess.value = "";
  
  try {
    const response = await apiClient.post("/api/auth/me/update/", formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    // The backend returns { user: { ... } }
    onSettingsUpdated(response.data.user);
    profileSuccess.value = "Your profile has been updated.";
  } catch (err) {
    profileError.value = err?.response?.data?.error || "Failed to update profile.";
  } finally {
    profileLoading.value = false;
  }
}

const currentTime = ref("");
const currentDate = ref("");
let timeInterval = null;

const courseAnnouncement = ref("");
const announcementSaving = ref(false);

const updateTime = () => {
  const now = new Date();
  todayCalendarKey.value = calendarDayKey(now);
  currentTime.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  currentDate.value = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
};

async function saveAnnouncement() {
  if (!selectedCourse.value) return;
  announcementSaving.value = true;
  error.value = "";
  try {
    const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
    await axios.put(`${backendBaseUrl}/api/instructor/subjects/${selectedCourse.value.id}/`, {
      announcements: courseAnnouncement.value
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
    });
    selectedCourse.value.announcements = courseAnnouncement.value;

    courseAnnouncement.value = "";
    showSuccess('Announcement posted', 'Your announcement is now visible to students.');
  } catch (err) {
    console.error("Failed to save announcement");
    error.value = "Failed to post announcement.";
  } finally {
    announcementSaving.value = false;
  }
}

const confirmOpen = ref(false);
const confirmTitle = ref("");
const confirmMessage = ref("");
const confirmVariant = ref("danger");
const confirmConfirmText = ref("Confirm");
const confirmCancelText = ref("Cancel");
let pendingConfirm = null;

function openConfirm(opts) {
  confirmTitle.value = opts.title;
  confirmMessage.value = opts.message;
  confirmVariant.value = opts.variant ?? "danger";
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

function requestDeleteAnnouncement() {
  openConfirm({
    title: "Delete Announcement?",
    message: "Students will no longer see this announcement.",
    confirmText: "Delete",
    variant: "danger",
    onConfirm: deleteAnnouncement,
  });
}

async function deleteAnnouncement() {
  if (!selectedCourse.value) return;
  announcementSaving.value = true;
  error.value = "";
  try {
    const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
    await axios.put(`${backendBaseUrl}/api/instructor/subjects/${selectedCourse.value.id}/`, {
      announcements: ""
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
    });
    selectedCourse.value.announcements = "";
    courseAnnouncement.value = "";
    showSuccess('Announcement deleted', 'The announcement was removed.');
  } catch (err) {
    console.error("Failed to delete announcement");
    error.value = "Failed to delete announcement.";
  } finally {
    announcementSaving.value = false;
  }
}

function requestLogout() {
  openConfirm({
    title: "Log out?",
    message: "You'll be signed out and returned to the login page. Your Google session will also be cleared.",
    confirmText: "Log out",
    variant: "neutral",
    onConfirm: performLogout,
  });
}

function performLogout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("role");
  localStorage.removeItem("user");
  router.push("/");
}
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: backendBaseUrl,
});

let refreshInFlight = null;

async function refreshAccessToken() {
  if (refreshInFlight) return refreshInFlight;
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    performLogout();
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
    .catch((err) => {
      performLogout();
      throw err;
    })
    .finally(() => {
      refreshInFlight = null;
    });

  return refreshInFlight;
}

apiClient.interceptors.request.use((config) => {
  const access = localStorage.getItem("access_token");
  if (access) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (err) => {
    const status = err?.response?.status;
    const original = err?.config;
    if (status === 401 && original && !original._retry) {
      original._retry = true;
      try {
        const nextAccess = await refreshAccessToken();
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${nextAccess}`;
        return apiClient(original);
      } catch (refreshErr) {
        throw refreshErr;
      }
    }
    throw err;
  },
);

const activeCourseTab = ref("uploaded-exams");
const showUploadExamPanel = ref(false);
const subjects = ref([]);
const subjectsLoading = ref(false);
const selectedSubjectId = ref(null);
const selectedSubjectSetId = ref("");
const courseBannerInput = ref(null);
const bannerUploading = ref(false);
const newSubjectSetName = ref("");
const subjectSets = ref([]);
const subjectSetsLoading = ref(false);

const subjectStudents = ref([]);
const studentsLoading = ref(false);
const subjectStudentEmail = ref("");
const examSets = ref([]);
const examSetsLoading = ref(false);
const examUploading = ref(false);
const examProgressRows = ref([]);
const examProgressLoading = ref(false);
const examProgressError = ref("");
const selectedProgressStudentEmail = ref("");
const progressView = ref("student");
const progressSort = ref("student_asc");
const integrityReportOpen = ref(false);
const integrityReportLoading = ref(false);
const integrityReportError = ref("");
const integrityReportData = ref({});
const gradingSaving = ref(false);
const gradingError = ref("");
const gradingMessage = ref("");
const reviewCheckedAnswers = ref(false);
const gradedSubjectiveCount = computed(() => (
  integrityReportData.value.subjective_answers || []
).filter(answer => answer.awarded_points != null).length);
const pendingSubjectiveAnswers = computed(() => (
  integrityReportData.value.subjective_answers || []
).filter(answer => answer.awarded_points == null));
const visibleSubjectiveAnswers = computed(() => (
  reviewCheckedAnswers.value
    ? integrityReportData.value.subjective_answers || []
    : pendingSubjectiveAnswers.value
));
const displayedEvidence = computed(() => groupExamEvidence(integrityReportData.value.evidence));
const evidenceImages = computed(() => displayedEvidence.value.evidence);
const snapshotImages = computed(() => displayedEvidence.value.snapshots);
const activeIrTab = ref('log');
const selectedProgressSetId = ref(null);
const selectedProgressExamId = ref(null);
const newExamTitle = ref("");
const newExamStartAt = ref("");
const newExamDueAt = ref("");
const newExamMaxAttempts = ref(1);
const newExamTimeLimit = ref(60);
const newExamAllowBacktracking = ref(true);
const newExamAssignedSet = ref("");
const upcomingExamRows = ref([]);
const upcomingLoading = ref(false);
const bulkEnrollEmails = ref("");
const bulkEnrollLoading = ref(false);
const bulkEnrollResult = ref(null);
const timelineSearch = ref("");
const calendarWeekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
const selectedCalendarDay = ref(calendarDayKey(new Date()));
const todayCalendarKey = ref(calendarDayKey(new Date()));
const courseFilter = ref("all");
const courseSearch = ref("");
const courseSort = ref("name_asc");
const courseView = ref("card");
const examSearch = ref("");
const examStatusFilter = ref("all");
const bankQuestions = ref([]);
const bankBatches = ref([]);
const bankLoading = ref(false);
const bankSaving = ref(false);
const bankEditorMode = ref('create');
const bankBatchName = ref('Manual questions');
const bankImportBatchName = ref('');
const bankSearch = ref("");
const bankTypeFilter = ref('all');
const bankSelectSearch = ref("");
const bankSelectType = ref('all');
const bankImportFormat = ref('aiken');
const selectedBankQuestionIds = ref([]);
const filteredBankBatches = computed(() => bankBatches.value.map(batch => ({
  ...batch,
  questions: batch.questions.filter(item =>
    (bankTypeFilter.value === 'all' || item.question_type === bankTypeFilter.value)
    && (batch.name.toLowerCase().includes(bankSearch.value.toLowerCase())
      || item.question_text.toLowerCase().includes(bankSearch.value.toLowerCase())),
  ),
})).filter(batch => batch.questions.length));
const selectableBankBatches = computed(() => bankBatches.value.map(batch => ({
  ...batch,
  questions: batch.questions.filter(item =>
    (bankSelectType.value === 'all' || item.question_type === bankSelectType.value)
    && (batch.name.toLowerCase().includes(bankSelectSearch.value.toLowerCase())
      || item.question_text.toLowerCase().includes(bankSelectSearch.value.toLowerCase())),
  ),
})).filter(batch => batch.questions.length));
const studentSearch = ref("");
const showBatchEnroll = ref(false);
const progressStudentSearch = ref("");

const managingExam = ref(null);
const examQuestions = ref([]);
const examBankItemIds = computed(() => new Set(examQuestions.value.map(question => question.bank_item_id).filter(Boolean)));
const availableBankQuestions = computed(() => bankQuestions.value.filter(item => !examBankItemIds.value.has(item.id)));
const examIsFinal = ref(false);
const questionsLoading = ref(false);
const restrictionsSaving = ref(false);
const examRestrictions = ref({
  gaze_above: true,
  gaze_below: true,
  gaze_left: true,
  gaze_right: true,
  gadgets: true,
});
const examRequiresAllRestrictions = computed(() =>
  examQuestions.value.length === 0
  || !examQuestions.value.some(question => question.question_type === 'essay'),
);
const newQ = ref({ type: 'multiple_choice', text: '', choices: ['', '', '', ''], correctIdx: 0, enumerationItems: ['', '', ''], points: '', correctAnswer: '', caseSensitive: false });
const bulkText = ref("");
const aikenFileName = ref("");

const statsExam = ref(null);
const statsLoading = ref(false);
const examStatsSets = ref([]);
const examStatsExaminees = ref([]);
let statsPollInterval = null;
let statsFetchGeneration = 0;
const statsSnapshotObjectUrls = new Map();

function releaseStatsSnapshotUrls(keepSources = new Set()) {
  for (const [source, objectUrl] of statsSnapshotObjectUrls) {
    if (keepSources.has(source)) continue;
    URL.revokeObjectURL(objectUrl);
    statsSnapshotObjectUrls.delete(source);
  }
}

async function attachStatsSnapshotUrls(examinees) {
  const rows = examinees || [];
  await Promise.all(rows.map(async (row) => {
    const source = row.snapshot_url;
    row.snapshot_display_url = source ? statsSnapshotObjectUrls.get(source) || null : null;
    if (!source || row.snapshot_display_url) return;
    try {
      const response = await apiClient.get(source, { responseType: 'blob' });
      if (response.data?.size > 0) {
        const objectUrl = URL.createObjectURL(response.data);
        statsSnapshotObjectUrls.set(source, objectUrl);
        row.snapshot_display_url = objectUrl;
      }
    } catch {
      row.snapshot_display_url = null;
    }
  }));
  return rows;
}

// Cache flags: skip re-fetching on revisit
const subjectsLoaded = ref(false);
const upcomingLoaded = ref(false);
const examSetsLoaded = ref(false);
const subjectSetsLoaded = ref(false);
const examProgressLoaded = ref(false);

const message = ref("");
const messageTitle = ref("");
function showSuccess(title, detail) {
  messageTitle.value = title;
  message.value = detail;
}
const error = ref("");
const archiveBusyId = ref(null);

const activeCourseLabel = computed(() => {
  if (!selectedSubjectId.value) return "";
  const found = subjects.value.find((s) => Number(s.id) === Number(selectedSubjectId.value));
  if (!found) return "";
  return `${found.code} - ${found.name}`;
});

const selectedCourse = computed(() => {
  if (!selectedSubjectId.value) return null;
  return subjects.value.find((s) => Number(s.id) === Number(selectedSubjectId.value)) || null;
});

const activeSetLabel = computed(() => {
  if (!selectedSubjectSetId.value) return "";
  const found = subjectSets.value.find((s) => Number(s.id) === Number(selectedSubjectSetId.value));
  return found?.name || "";
});

const sortedExamSets = computed(() =>
  [...(examSets.value || [])].sort(compareExamsNewestFirst)
);

const dashboardTitle = computed(() => {
  if (activeNav.value === 'dashboard') return 'Dashboard';
  if (activeNav.value === 'archive') return 'Archive';
  if (activeNav.value === 'courses' && isCourseDetailRoute.value && selectedCourse.value) {
    return selectedCourse.value.name;
  }
  if (activeNav.value === 'courses') return 'My Courses';
  if (activeNav.value === 'settings') return 'Profile';
  return '';
});

const coursesSummary = computed(() => {
  const all = subjects.value.filter((subject) => !subject.is_archived);
  return {
    total: all.length,
    students: all.reduce((sum, s) => sum + (s.student_count || 0), 0),
    filtered: displayedCourses.value.length,
  };
});

const courseDetailStats = computed(() => ({
  students: selectedCourse.value?.student_count || 0,
  sections: subjectSets.value?.length || 0,
  exams: examSets.value?.length || 0,
  publishedExams: (examSets.value || []).filter((e) => e.is_final).length,
}));

const courseDetailMeta = computed(() => {
  const { students, sections, exams, publishedExams } = courseDetailStats.value;
  const bits = [
    `${students} ${students === 1 ? "student" : "students"}`,
    `${sections} ${sections === 1 ? "section" : "sections"}`,
    `${exams} ${exams === 1 ? "exam" : "exams"}`,
  ];
  if (publishedExams) bits.push(`${publishedExams} published`);
  return bits.join(" · ");
});

function examLifecycle(exam) {
  if (!exam?.is_final) return "draft";
  const now = Date.now();
  const start = exam.available_from ? new Date(exam.available_from).getTime() : NaN;
  const due = exam.due_at ? new Date(exam.due_at).getTime() : NaN;
  if (Number.isFinite(start) && start > now) return "upcoming";
  if (Number.isFinite(due) && due < now) return "ended";
  return "open";
}

function examLifecycleLabel(exam) {
  const key = examLifecycle(exam);
  return { upcoming: "Opens later", open: "Open now", ended: "Ended", draft: "Draft" }[key] || "";
}

const displayedExams = computed(() => {
  const query = examSearch.value.toLowerCase();
  let rows = sortedExamSets.value || [];
  if (examStatusFilter.value === "published") rows = rows.filter((e) => e.is_final);
  if (examStatusFilter.value === "draft") rows = rows.filter((e) => !e.is_final);
  if (query) {
    rows = rows.filter((e) => String(e.title || "").toLowerCase().includes(query));
  }
  return rows;
});

const displayedStudents = computed(() => {
  const query = studentSearch.value.toLowerCase();
  const rows = subjectStudents.value || [];
  if (!query) return rows;
  return rows.filter((s) => String(s.email || "").toLowerCase().includes(query));
});

const courseHeroPhotoStyle = computed(() => {
  const photo = selectedCourse.value?.display_photo;
  if (!photo) return {};
  const url = photo.startsWith('http') ? photo : `${backendBaseUrl}${photo}`;
  return { backgroundImage: `url(${url})` };
});

const activeNav = computed(() => {
  if (route.path.startsWith("/instructor/archive")) return "archive";
  if (route.path.startsWith("/instructor/courses")) return "courses";
  if (route.path.startsWith("/instructor/settings")) return "settings";
  return "dashboard";
});

function formatTimeOnly(raw) {
  if (!raw) return "23:59";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return "23:59";
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute:'2-digit' });
}

const filteredUpcomingExams = computed(() => {
  const now = Date.now();
  const query = timelineSearch.value.toLowerCase();
  let rows = (upcomingExamRows.value || []).filter((exam) => {
    if (subjects.value.some((subject) => subject.is_archived && Number(subject.id) === Number(exam.subject_id))) return false;
    if (!instructorExamOnDashboard(exam, { now, withinDays: 3650 })) return false;
    if (!query) return true;
    return (
      String(exam?.title || "").toLowerCase().includes(query) ||
      String(exam?.subject_name || "").toLowerCase().includes(query) ||
      String(exam?.subject_code || "").toLowerCase().includes(query)
    );
  });

  return rows.sort((a, b) => examAnchorTimestamp(a) - examAnchorTimestamp(b));
});

const calendarMonthLabel = computed(() => calendarMonth.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }));
const calendarDays = computed(() => calendarMonthDays(calendarMonth.value, filteredUpcomingExams.value));
const selectedCalendarLabel = computed(() => {
  const date = new Date(`${selectedCalendarDay.value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? 'Select a day' : date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
});
const selectedCalendarExams = computed(() => filteredUpcomingExams.value.filter(
  (exam) => calendarDayKey(examTimelineDisplayAt(exam)) === selectedCalendarDay.value,
));

function selectCalendarDate(date) {
  calendarMonth.value = new Date(date.getFullYear(), date.getMonth(), 1);
  selectedCalendarDay.value = calendarDayKey(date);
}

function moveCalendarMonth(offset) {
  const next = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth() + offset, 1);
  calendarMonth.value = next;
  const firstExam = filteredUpcomingExams.value.find((exam) => {
    const date = new Date(examTimelineDisplayAt(exam));
    return date.getFullYear() === next.getFullYear() && date.getMonth() === next.getMonth();
  });
  selectedCalendarDay.value = firstExam ? calendarDayKey(examTimelineDisplayAt(firstExam)) : calendarDayKey(next);
}

function selectCalendarToday() {
  selectCalendarDate(new Date());
}

function selectNextCalendarExam() {
  const selectedAt = new Date(`${selectedCalendarDay.value}T00:00:00`).getTime();
  const next = filteredUpcomingExams.value.find((exam) => examAnchorTimestamp(exam) >= selectedAt)
    || filteredUpcomingExams.value[0];
  if (next) selectCalendarDate(new Date(examTimelineDisplayAt(next)));
}

function calendarExamTimeLabel(exam) {
  const start = exam.available_from ? new Date(exam.available_from).getTime() : NaN;
  const prefix = Number.isFinite(start) && start > Date.now() ? 'Opens' : exam.due_at ? 'Due' : 'Available';
  return `${prefix} ${formatExamTimelineTime(exam)}`;
}

let calendarInitiallyFocused = false;
watch([filteredUpcomingExams, upcomingLoading], ([rows, loading]) => {
  if (calendarInitiallyFocused || loading || !rows.length) return;
  const nextDate = new Date(examTimelineDisplayAt(rows[0]));
  if (Number.isNaN(nextDate.getTime())) return;
  selectCalendarDate(nextDate);
  calendarInitiallyFocused = true;
});

const displayedCourses = computed(() => {
  const query = courseSearch.value.toLowerCase();
  let rows = subjects.value.filter((subject) => !subject.is_archived);
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
const archivedCourses = computed(() => subjects.value.filter((subject) => subject.is_archived)
  .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''))));

function progressStudentName(rawEmail) {
  const email = String(rawEmail || "").toLowerCase();
  const local = email.includes("@") ? email.split("@")[0] : email;
  const pretty = local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  return pretty || email;
}

const examProgressStudents = computed(() => {
  const map = new Map();
  for (const row of examProgressRows.value || []) {
    const email = String(row.student_email || "").toLowerCase();
    if (!email || map.has(email)) continue;
    map.set(email, { email, name: progressStudentName(email) });
  }
  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
});

const progressSets = computed(() => {
  const map = new Map();
  for (const row of examProgressRows.value || []) {
    const sid = row.student_set_id;
    if (!sid) continue;
    if (!map.has(sid)) {
      map.set(sid, { id: sid, name: row.student_set_name || `Set ${sid}`, emails: new Set() });
    }
    map.get(sid).emails.add(String(row.student_email || "").toLowerCase());
  }
  return Array.from(map.values())
    .map(s => ({ ...s, studentCount: s.emails.size }))
    .sort((a, b) => a.name.localeCompare(b.name));
});

const progressExams = computed(() => {
  const map = new Map();
  for (const row of examProgressRows.value || []) {
    if (!map.has(row.exam_set_id)) {
      map.set(row.exam_set_id, { id: row.exam_set_id, title: row.exam_title, created_at: row.created_at });
    }
  }
  return Array.from(map.values()).sort(compareExamsNewestFirst);
});

const progressExamsForSelectedSet = computed(() => {
  if (!selectedProgressSetId.value) return [];
  const studentCounts = new Map();
  for (const row of examProgressRows.value || []) {
    if (row.student_set_id !== selectedProgressSetId.value) continue;
    if (!studentCounts.has(row.exam_set_id)) studentCounts.set(row.exam_set_id, new Set());
    studentCounts.get(row.exam_set_id).add(String(row.student_email || "").toLowerCase());
  }
  return progressExams.value
    .filter((exam) => studentCounts.has(exam.id))
    .map((exam) => ({ ...exam, studentCount: studentCounts.get(exam.id).size }));
});

const selectedProgressExamTitle = computed(() => {
  const exam = progressExamsForSelectedSet.value.find(
    (item) => item.id === selectedProgressExamId.value,
  );
  return exam ? formatDisplayTitle(exam.title) : "Select an exam or quiz";
});

const selectedSetExamRows = computed(() => {
  if (!selectedProgressSetId.value || !selectedProgressExamId.value) return [];
  return (examProgressRows.value || []).filter(
    row =>
      row.student_set_id === selectedProgressSetId.value &&
      row.exam_set_id === selectedProgressExamId.value
  );
});

function compareProgressValues(a, b, field, direction) {
  const aValue = a[field];
  const bValue = b[field];
  const aMissing = aValue === null || aValue === undefined || aValue === "";
  const bMissing = bValue === null || bValue === undefined || bValue === "";
  if (aMissing !== bMissing) return aMissing ? 1 : -1;
  if (!aMissing && Number(aValue) !== Number(bValue)) {
    return direction * (Number(aValue) - Number(bValue));
  }
  return progressStudentName(a.student_email).localeCompare(progressStudentName(b.student_email));
}

const sortedSelectedSetExamRows = computed(() => {
  const rows = [...selectedSetExamRows.value];
  const [field, direction] = progressSort.value.split("_");
  if (field === "score" || field === "integrity") {
    const dataField = field === "integrity" ? "integrity_score" : "score";
    return rows.sort((a, b) => compareProgressValues(a, b, dataField, direction === "asc" ? 1 : -1));
  }
  return rows.sort((a, b) => {
    const comparison = progressStudentName(a.student_email).localeCompare(progressStudentName(b.student_email));
    return direction === "desc" ? -comparison : comparison;
  });
});

const selectedSetProgressRows = computed(() => {
  if (!selectedProgressSetId.value) return [];
  return (examProgressRows.value || []).filter(
    row => row.student_set_id === selectedProgressSetId.value
  );
});

function progressStudentsBySet(setId) {
  const map = new Map();
  for (const row of examProgressRows.value || []) {
    if (row.student_set_id !== setId) continue;
    const email = String(row.student_email || '').toLowerCase();
    if (!email || map.has(email)) continue;
    map.set(email, { email, name: progressStudentName(email) });
  }
  const direction = progressSort.value === "student_desc" ? -1 : 1;
  const rows = Array.from(map.values()).sort((a, b) => direction * a.name.localeCompare(b.name));
  const query = progressStudentSearch.value.toLowerCase();
  if (!query) return rows;
  return rows.filter(
    (s) => s.name.toLowerCase().includes(query) || s.email.toLowerCase().includes(query),
  );
}

const selectedStudentProgressRows = computed(() => {
  if (!selectedProgressStudentEmail.value || !selectedProgressSetId.value) return [];
  return (examProgressRows.value || []).filter(
    (row) => row.student_set_id === selectedProgressSetId.value
      && String(row.student_email || "").toLowerCase() === selectedProgressStudentEmail.value,
  ).sort(compareExamsNewestFirst);
});

function courseBannerClass(index) {
  const variants = ["teal", "gold", "blue", "gray"];
  return `banner-${variants[index % variants.length]}`;
}

const isCourseDetailRoute = computed(() => Boolean(route.params.courseId));
const isSetDetailRoute = computed(() => Boolean(route.params.courseId && route.params.setId));
const courseActionsMenu = ref(null);

function closeCourseActionsMenu() {
  if (!courseActionsMenu.value) return;
  courseActionsMenu.value.open = false;
  courseActionsMenu.value.querySelector('summary')?.focus();
}

function closeCourseActionsMenuOnOutsideClick(event) {
  if (courseActionsMenu.value && !courseActionsMenu.value.contains(event.target)) {
    courseActionsMenu.value.open = false;
  }
}

onMounted(() => document.addEventListener('pointerdown', closeCourseActionsMenuOnOutsideClick));
onUnmounted(() => document.removeEventListener('pointerdown', closeCourseActionsMenuOnOutsideClick));

function goDashboard() {
  router.push("/instructor/dashboard");
}

function goCourses() {
  router.push("/instructor/courses");
}

function goArchive() {
  router.push("/instructor/archive");
}

function goSettings() {
  router.push("/instructor/settings");
}

function openCourse(courseId) {
  router.push(`/instructor/courses/${courseId}`);
}

function openSetDetail(setId) {
  if (!selectedSubjectId.value) return;
  activeCourseTab.value = "sets";
  router.push(`/instructor/courses/${selectedSubjectId.value}/sets/${setId}`);
}

function backToSetsList() {
  if (!selectedSubjectId.value) return;
  router.push(`/instructor/courses/${selectedSubjectId.value}`);
}

function syncSelectedCourseFromRoute() {
  const courseId = route.params.courseId;
  if (!courseId) {
    selectedSubjectId.value = null;
    selectedSubjectSetId.value = "";
    subjectSets.value = [];
    examSets.value = [];
    subjectStudents.value = [];
    return;
  }
  selectedSubjectId.value = Number(courseId);
  if (route.params.setId) {
    selectedSubjectSetId.value = String(route.params.setId);
    activeCourseTab.value = "sets";
  } else {
    selectedSubjectSetId.value = "";
  }
}

async function fetchSubjects() {
  subjectsLoading.value = true;
  error.value = "";
  try {
    const { data } = await apiClient.get("/api/instructor/subjects/");
    subjects.value = data.subjects || [];
    subjectsLoaded.value = true;
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to load courses.";
  } finally {
    subjectsLoading.value = false;
  }
}

async function fetchSubjectStudents() {
  if (!selectedSubjectSetId.value) {
    subjectStudents.value = [];
    return;
  }
  studentsLoading.value = true;
  error.value = "";
  try {
    const params = { student_set_id: selectedSubjectSetId.value };
    const { data } = await apiClient.get("/api/instructor/students/", { params });
    subjectStudents.value = data.students || [];
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to load set students.";
  } finally {
    studentsLoading.value = false;
  }
}

async function fetchSubjectSets() {
  if (!selectedSubjectId.value) {
    subjectSets.value = [];
    return;
  }
  subjectSetsLoading.value = true;
  error.value = "";
  try {
    const { data } = await apiClient.get(`/api/instructor/subjects/${selectedSubjectId.value}/sets/`);
    subjectSets.value = data.sets || [];
    subjectSetsLoaded.value = true;
    if (selectedSubjectSetId.value) {
      const stillExists = subjectSets.value.some(
        (row) => Number(row.id) === Number(selectedSubjectSetId.value),
      );
      if (!stillExists) {
        selectedSubjectSetId.value = "";
      }
    }
    if (!selectedSubjectSetId.value && subjectSets.value.length) {
      selectedSubjectSetId.value = String(subjectSets.value[0].id);
    }
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to load sets.";
  } finally {
    subjectSetsLoading.value = false;
  }
}

async function fetchExamSets() {
  if (!selectedSubjectId.value) {
    examSets.value = [];
    return;
  }
  examSetsLoading.value = true;
  error.value = "";
  try {
    const { data } = await apiClient.get(`/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/`);
    const targetSub = subjects.value.find(s => s.id === selectedSubjectId.value);
    examSets.value = (data.exam_sets || []).map(e => ({
      ...e,
      subject_id: e.subject_id || selectedSubjectId.value,
      subject_code: e.subject_code || targetSub?.code || '',
      subject_name: e.subject_name || targetSub?.name || '',
    }));
    examSetsLoaded.value = true;
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to load uploaded exams.";
  } finally {
    examSetsLoading.value = false;
  }
}

function onEvidenceImageError(event) {
  const img = event?.target;
  if (!img) return;
  img.style.display = 'none';
  const parent = img.parentElement;
  if (parent && !parent.querySelector('.ir-shot-missing')) {
    const note = document.createElement('div');
    note.className = 'ir-shot-missing';
    note.textContent = 'Image unavailable';
    parent.insertBefore(note, img);
  }
}

function formatReportTime(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return String(iso);
  }
}

const GAZE_EVENT_TYPES = new Set(['gaze_violation', 'gaze_no_face']);

function isGazeEvent(eventType) {
  return GAZE_EVENT_TYPES.has(eventType);
}

function formatEventType(eventType) {
  const labels = {
    gaze_violation: 'Gaze away',
    gaze_no_face: 'Face not visible',
    tab_switch: 'Tab switch',
    split_screen: 'Split screen',
    extended_monitor: 'Extended monitor',
    periodic_capture: 'Webcam snapshot',
    exam_terminated: 'Exam terminated',
    exam_submitted: 'Exam submitted',
    screenshot_attempt: 'Screenshot attempt',
    screen_share_stopped: 'Screen sharing stopped',
    warning_shown: 'Warning displayed',
    copy_attempt: 'Copy attempt',
    cut_attempt: 'Cut attempt',
    right_click: 'Right-click attempt',
    time_up: 'Time up',
  };
  return labels[eventType] || String(eventType || '').replace(/_/g, ' ');
}

function integrityScoreTone(score) {
  if (score == null || score === '') return 'ir-tone-neutral';
  const n = Number(score);
  if (Number.isNaN(n)) return 'ir-tone-neutral';
  if (n >= 85) return 'ir-tone-good';
  if (n >= 70) return 'ir-tone-warn';
  return 'ir-tone-bad';
}

function severityClass(severity) {
  const s = String(severity || '').toLowerCase();
  if (s === 'critical') return 'ir-sev-critical';
  if (s === 'warning') return 'ir-sev-warning';
  if (s === 'info') return 'ir-sev-info';
  return 'ir-sev-neutral';
}

async function openIntegrityReport(row) {
  // Accept subject_id from the row (passed from stats modal) or fall back to the sidebar selection.
  const subjectId = row?.subject_id || selectedSubjectId.value;
  if (!subjectId || !row?.exam_set_id || !row?.student_email) return;
  integrityReportOpen.value = true;
  integrityReportLoading.value = true;
  integrityReportError.value = '';
  integrityReportData.value = { _student_score: row.score ?? null, _student_email: row.student_email, _subject_id: subjectId };
  gradingError.value = '';
  gradingMessage.value = '';
  reviewCheckedAnswers.value = false;
  activeIrTab.value = row.pending_subjective_count > 0 ? 'answers' : 'log';
  try {
    const { data } = await apiClient.get(
      `/api/instructor/subjects/${subjectId}/exam-sets/${row.exam_set_id}/integrity-report/`,
      { params: { student_email: row.student_email } },
    );
    const subjectiveAnswers = (data.subjective_answers || []).map(answer => ({
      ...answer,
      _grade: answer.awarded_points ?? '',
    }));
    integrityReportData.value = {
      ...data,
      subjective_answers: subjectiveAnswers,
      _student_score: row.score ?? null,
      _subject_id: subjectId,
    };
    if (subjectiveAnswers.length && (row.pending_subjective_count > 0 || row.pending_subjective_count == null)) {
      activeIrTab.value = 'answers';
    }
  } catch (err) {
    integrityReportError.value = err?.response?.data?.error || 'Unable to load integrity report.';
  } finally {
    integrityReportLoading.value = false;
  }
}

async function fetchExamProgress() {
  if (!selectedSubjectId.value) {
    examProgressRows.value = [];
    return;
  }
  examProgressLoading.value = true;
  examProgressError.value = "";
  try {
    const { data } = await apiClient.get(`/api/instructor/subjects/${selectedSubjectId.value}/exam-progress/`);
    examProgressRows.value = data.progress || [];
    examProgressLoaded.value = true;
    if (!selectedProgressStudentEmail.value && examProgressRows.value.length) {
      selectedProgressStudentEmail.value = String(examProgressRows.value[0].student_email || "").toLowerCase();
    }
    if (
      selectedProgressStudentEmail.value &&
      !examProgressRows.value.some(
        (row) => String(row.student_email || "").toLowerCase() === selectedProgressStudentEmail.value,
      )
    ) {
      selectedProgressStudentEmail.value = examProgressRows.value.length
        ? String(examProgressRows.value[0].student_email || "").toLowerCase()
        : "";
    }
  } catch (err) {
    examProgressError.value = err?.response?.data?.error || "Unable to load exam progress.";
  } finally {
    examProgressLoading.value = false;
  }
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

function toDisplayDue(exam) {
  const startRaw = exam?.available_from;
  const dueRaw = exam?.due_at || exam?.deadline || exam?.created_at;

  if (!startRaw && !dueRaw) return "No date set";
  const startString = startRaw ? new Date(startRaw).toLocaleString([], { dateStyle: 'short', timeStyle: 'short'}) : 'Open';
  const endString = dueRaw ? new Date(dueRaw).toLocaleString([], { dateStyle: 'short', timeStyle: 'short'}) : 'No limit';
  return `${startString} - ${endString}`;
}

function toAbsoluteFileUrl(fileUrl) {
  if (!fileUrl) return "";
  if (String(fileUrl).startsWith("http://") || String(fileUrl).startsWith("https://")) return fileUrl;
  return `${backendBaseUrl}${fileUrl}`;
}

function openCourseBannerPicker() {
  closeCourseActionsMenu();
  courseBannerInput.value?.click();
}

async function uploadCourseBanner(event) {
  const file = event?.target?.files?.[0];
  if (!file || !selectedSubjectId.value) return;
  event.target.value = '';
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
    error.value = 'Use a JPG, PNG, or WebP image no larger than 5 MB.';
    return;
  }
  bannerUploading.value = true;
  try {
    const payload = new FormData();
    payload.append('display_photo', file);
    const { data } = await apiClient.patch(`/api/instructor/subjects/${selectedSubjectId.value}/`, payload);
    if (selectedCourse.value) selectedCourse.value.display_photo = data.display_photo;
    showSuccess('Banner updated', 'Your course banner has been changed.');
  } catch (err) {
    error.value = err?.response?.data?.error || 'Could not update the course banner.';
  } finally {
    bannerUploading.value = false;
  }
}

async function fetchUpcomingExams() {
  upcomingLoading.value = true;
  try {
    const { data } = await apiClient.get("/api/instructor/subjects/");
    const rows = data.subjects || [];
    const examLists = await Promise.all(
      rows.map(async (subject) => {
        const examResponse = await apiClient.get(`/api/instructor/subjects/${subject.id}/exam-sets/`);
        const exams = examResponse?.data?.exam_sets || [];
        return exams.map((exam) => ({
          ...exam,
          subject_id: subject.id,
          subject_code: subject.code,
          subject_name: subject.name,
          display_due: toDisplayDue(exam),
        }));
      }),
    );
    upcomingExamRows.value = examLists.flat().sort(compareExamsNewestFirst);
    upcomingLoaded.value = true;
  } catch {
    upcomingExamRows.value = [];
  } finally {
    upcomingLoading.value = false;
  }
}

async function enrollStudentToSubject() {
  if (!selectedSubjectSetId.value) {
    error.value = "Please select a student set.";
    return;
  }
  studentsLoading.value = true;
  error.value = "";
  message.value = "";
  try {
    await apiClient.post("/api/instructor/students/", {
      email: subjectStudentEmail.value.trim(),
      student_set_id: selectedSubjectSetId.value,
    });
    showSuccess('Student enrolled', 'The student was added to this course.');
    subjectStudentEmail.value = "";
    await fetchSubjects();
    await refreshSetsView();
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to enroll student.";
  } finally {
    studentsLoading.value = false;
  }
}

async function bulkEnrollToSet() {
  if (!selectedSubjectSetId.value) {
    error.value = "Please select a set first.";
    return;
  }
  if (!bulkEnrollEmails.value.trim()) {
    error.value = "Please enter one or more emails.";
    return;
  }
  bulkEnrollLoading.value = true;
  error.value = "";
  message.value = "";
  try {
    const { data } = await apiClient.post(
      `/api/instructor/sets/${selectedSubjectSetId.value}/enroll-bulk/`,
      { emails: bulkEnrollEmails.value },
    );
    bulkEnrollResult.value = data;
    showSuccess('Students enrolled', 'Batch enrollment finished.');
    bulkEnrollEmails.value = "";
    await fetchSubjects();
    await refreshSetsView();
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to batch enroll students.";
  } finally {
    bulkEnrollLoading.value = false;
  }
}

async function onXlsxUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (!selectedSubjectSetId.value) {
    error.value = "Please select a set first.";
    event.target.value = "";
    return;
  }

  bulkEnrollLoading.value = true;
  bulkEnrollResult.value = null;
  error.value = "";
  message.value = "";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await apiClient.post(
      `/api/instructor/sets/${selectedSubjectSetId.value}/enroll-bulk/`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    bulkEnrollResult.value = data;
    showSuccess('Students imported', `${data.added?.length || 0} student(s) enrolled from the Excel file.`);
    await fetchSubjects();
    await refreshSetsView();
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to import the Excel file.";
  } finally {
    bulkEnrollLoading.value = false;
    event.target.value = "";
  }
}

async function saveSubjectiveGrades() {
  const report = integrityReportData.value;
  if (!report?._subject_id || !report?.exam_set_id || !report?.student_email) return;
  gradingSaving.value = true;
  gradingError.value = '';
  gradingMessage.value = '';
  try {
    const grades = visibleSubjectiveAnswers.value.map(answer => ({
      answer_id: answer.answer_id,
      awarded_points: answer._grade === '' ? null : answer._grade,
    }));
    const { data } = await apiClient.patch(
      `/api/instructor/subjects/${report._subject_id}/exam-sets/${report.exam_set_id}/integrity-report/`,
      { grades },
      { params: { student_email: report.student_email } },
    );
    const subjectiveAnswers = (data.subjective_answers || []).map(answer => ({
      ...answer,
      _grade: answer.awarded_points ?? '',
    }));
    integrityReportData.value = {
      ...data,
      subjective_answers: subjectiveAnswers,
      _subject_id: report._subject_id,
      _student_score: data.submission?.score ?? report._student_score,
    };
    reviewCheckedAnswers.value = false;
    gradingMessage.value = data.manual_grading_complete
      ? 'All subjective answers are graded and the exam score has been updated.'
      : 'Grades saved. Unscored answers remain pending.';
    await fetchExamProgress();
  } catch (err) {
    gradingError.value = err?.response?.data?.error || 'Unable to save the grades.';
  } finally {
    gradingSaving.value = false;
  }
}

async function createSubjectSet() {
  if (!selectedSubjectId.value) {
    error.value = "Please select a course first.";
    return;
  }
  error.value = "";
  message.value = "";
  try {
    await apiClient.post(`/api/instructor/subjects/${selectedSubjectId.value}/sets/`, {
      name: newSubjectSetName.value.trim(),
    });
    showSuccess('Set created', 'The new set was added to this course.');
    newSubjectSetName.value = "";
    await fetchSubjects();
    await refreshSetsView();
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to create set.";
  }
}

function requestDeleteSubjectSet(setId) {
  if (!setId) return;
  openConfirm({
    title: "Delete this set?",
    message:
      "All enrollments in this set will be removed. Students may lose access unless enrolled in another set.",
    confirmText: "Delete set",
    variant: "danger",
    onConfirm: () => removeSubjectSetImpl(setId),
  });
}

async function removeSubjectSetImpl(setId) {
  error.value = "";
  message.value = "";
  try {
    await apiClient.delete(`/api/instructor/subjects/${selectedSubjectId.value}/sets/${setId}/`);
    showSuccess('Set deleted', 'The set was removed from this course.');
    if (Number(selectedSubjectSetId.value) === Number(setId)) {
      selectedSubjectSetId.value = "";
      subjectStudents.value = [];
    }
    await fetchSubjects();
    await refreshSetsView();
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to delete set.";
  }
}

function requestRemoveSubjectStudent(enrollmentId) {
  openConfirm({
    title: "Remove this student?",
    message: "They will no longer be enrolled in this student set.",
    confirmText: "Remove",
    variant: "danger",
    onConfirm: () => removeSubjectStudentImpl(enrollmentId),
  });
}

async function removeSubjectStudentImpl(enrollmentId) {
  error.value = "";
  message.value = "";
  try {
    await apiClient.delete(`/api/instructor/students/${enrollmentId}/`);
    showSuccess('Student removed from set', 'The student is no longer assigned to this set.');
    await refreshSetsView();
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to remove student.";
  }
}

function requestArchiveSubject() {
  if (!selectedSubjectId.value) return;
  closeCourseActionsMenu();
  openConfirm({
    title: "Archive this course?",
    message: "This hides the course from your active list. Students and other assigned instructors keep access, and you can restore it anytime.",
    confirmText: "Archive course",
    variant: "neutral",
    onConfirm: archiveSubjectImpl,
  });
}

async function archiveSubjectImpl() {
  const course = selectedCourse.value;
  if (!course) return;
  error.value = "";
  message.value = "";
  archiveBusyId.value = course.id;
  try {
    await apiClient.patch(`/api/instructor/subjects/${course.id}/`, { archived: true });
    course.is_archived = true;
    goArchive();
    showSuccess('Course archived', 'You can restore it from your Archive page.');
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to archive course.";
  } finally {
    archiveBusyId.value = null;
  }
}

async function restoreSubject(course) {
  error.value = "";
  message.value = "";
  archiveBusyId.value = course.id;
  try {
    await apiClient.patch(`/api/instructor/subjects/${course.id}/`, { archived: false });
    course.is_archived = false;
    showSuccess('Course restored', `${course.name} is back in your active courses.`);
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to restore course.";
  } finally {
    archiveBusyId.value = null;
  }
}

async function createExamSet() {
  if (!selectedSubjectId.value) {
    error.value = "Please select a course first.";
    return;
  }
  if (!newExamStartAt.value) {
    error.value = "Please set a start date/time.";
    return;
  }
  if (!newExamDueAt.value) {
    error.value = "Please set a due date/time.";
    return;
  }
  // Guard against double-submit (double-click / fast re-submit)
  if (examUploading.value) return;
  examUploading.value = true;
  error.value = "";
  message.value = "";
  try {
    const payload = new FormData();
    payload.append("title", newExamTitle.value.trim());
    payload.append("available_from", localDatetimeInputToApi(newExamStartAt.value));
    payload.append("due_at", localDatetimeInputToApi(newExamDueAt.value));
    payload.append("max_attempts", newExamMaxAttempts.value);
    payload.append("time_limit", newExamTimeLimit.value);
    payload.append("allow_backtracking", newExamAllowBacktracking.value);
    const setsArray = newExamAssignedSet.value ? [Number(newExamAssignedSet.value)] : [];
    payload.append("assigned_sets", JSON.stringify(setsArray));
    const { data } = await apiClient.post(`/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/`, payload);
    showSuccess('Exam created', 'The draft is ready. Select questions from the course bank.');
    newExamTitle.value = "";
    newExamStartAt.value = "";
    newExamDueAt.value = "";
    newExamMaxAttempts.value = 1;
    newExamTimeLimit.value = 60;
    newExamAllowBacktracking.value = true;
    newExamAssignedSet.value = "";
    showUploadExamPanel.value = false;
    await fetchExamSets();
    await fetchQuestionBank();
    await fetchUpcomingExams();
    const createdExam = examSets.value.find(exam => exam.id === data.id);
    if (createdExam) openManageQuestions(createdExam);
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to upload exam.";
  } finally {
    examUploading.value = false;
  }
}

function requestRemoveExamSet(examSetId) {
  openConfirm({
    title: "Delete this exam?",
    message: "This permanently deletes the exam and all related student records — submissions, scores, proctoring evidence, and integrity reports. Exam Progress will update immediately.",
    confirmText: "Delete exam",
    variant: "danger",
    onConfirm: () => removeExamSetImpl(examSetId),
  });
}

async function removeExamSetImpl(examSetId) {
  if (!selectedSubjectId.value) return;
  error.value = "";
  message.value = "";
  try {
    await apiClient.delete(`/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/${examSetId}/`);
    showSuccess('Exam deleted', 'The exam and related student records were removed.');
    // Drop local progress rows for this exam immediately, then refresh lists.
    examProgressRows.value = (examProgressRows.value || []).filter(
      (row) => Number(row.exam_set_id) !== Number(examSetId),
    );
    examProgressLoaded.value = false;
    if (statsExam.value && Number(statsExam.value.id) === Number(examSetId)) {
      closeExamStats();
    }
    if (managingExam.value && Number(managingExam.value.id) === Number(examSetId)) {
      closeManageQuestions();
    }
    await fetchExamSets();
    await fetchUpcomingExams();
    if (activeCourseTab.value === "exam-progress") {
      await fetchExamProgress();
    }
  } catch (err) {
    error.value = err?.response?.data?.error || "Unable to delete exam.";
  }
}

function openManageQuestions(exam) {
  managingExam.value = exam;
  selectedBankQuestionIds.value = [];
  bankSelectSearch.value = '';
  bankSelectType.value = 'all';
  fetchExamQuestions();
  fetchQuestionBank();
}

function closeManageQuestions() {
  managingExam.value = null;
  examQuestions.value = [];
  selectedBankQuestionIds.value = [];
  examRestrictions.value = {
    gaze_above: true,
    gaze_below: true,
    gaze_left: true,
    gaze_right: true,
    gadgets: true,
  };
}

function addChoice() {
  newQ.value.choices.push("");
}

function removeChoice(idx) {
  newQ.value.choices.splice(idx, 1);
  if (newQ.value.correctIdx === idx) newQ.value.correctIdx = 0;
  else if (newQ.value.correctIdx > idx) newQ.value.correctIdx--;
}

function addEnumerationItem() {
  newQ.value.enumerationItems.push("");
}

function removeEnumerationItem(idx) {
  if (newQ.value.enumerationItems.length > 1) {
    newQ.value.enumerationItems.splice(idx, 1);
  }
}

async function fetchExamQuestions() {
  if (!managingExam.value || !selectedSubjectId.value) return;
  questionsLoading.value = true;
  try {
    const { data } = await apiClient.get(`/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/${managingExam.value.id}/questions/`);
    examQuestions.value = data.questions || [];
    examIsFinal.value = data.is_final || false;
    examRestrictions.value = {
      gaze_above: data.proctoring_restrictions?.gaze_above ?? true,
      gaze_below: data.proctoring_restrictions?.gaze_below ?? true,
      gaze_left: data.proctoring_restrictions?.gaze_left ?? true,
      gaze_right: data.proctoring_restrictions?.gaze_right ?? true,
      gadgets: data.proctoring_restrictions?.gadgets ?? true,
    };
  } catch (err) {
    error.value = "Failed to load questions.";
  } finally {
    questionsLoading.value = false;
  }
}

async function saveExamRestrictions() {
  if (!managingExam.value || !selectedSubjectId.value || examIsFinal.value) return;
  if (examRequiresAllRestrictions.value) {
    examRestrictions.value = {
      gaze_above: true,
      gaze_below: true,
      gaze_left: true,
      gaze_right: true,
      gadgets: true,
    };
    return;
  }

  restrictionsSaving.value = true;
  message.value = '';
  error.value = '';
  try {
    const { data } = await apiClient.patch(
      `/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/${managingExam.value.id}/`,
      { proctoring_restrictions: { ...examRestrictions.value } },
    );
    examRestrictions.value = { ...data.proctoring_restrictions };
    showSuccess('Proctoring restrictions saved', 'The exam’s proctoring settings were updated.');
  } catch (err) {
    error.value = err?.response?.data?.error || 'Failed to save proctoring restrictions.';
    await fetchExamQuestions();
  } finally {
    restrictionsSaving.value = false;
  }
}

function questionTypeLabel(type) {
  return ({ multiple_choice: 'Multiple choice', identification: 'Identification', enumeration: 'Enumeration', essay: 'Essay' })[type] || type;
}

async function fetchQuestionBank() {
  const subjectId = selectedSubjectId.value;
  if (!subjectId) {
    bankQuestions.value = [];
    bankBatches.value = [];
    return;
  }
  bankLoading.value = true;
  try {
    const { data } = await apiClient.get(`/api/instructor/subjects/${subjectId}/question-bank/`);
    if (selectedSubjectId.value === subjectId) {
      bankBatches.value = data.batches || [];
      bankQuestions.value = bankBatches.value.flatMap(batch => batch.questions);
    }
  } catch (err) {
    error.value = err?.response?.data?.error || 'Unable to load the question bank.';
  } finally {
    bankLoading.value = false;
  }
}

async function addBankQuestion() {
  if (!selectedSubjectId.value) return;

  const payload = {
    question_type: newQ.value.type,
    question_text: newQ.value.text,
    batch_name: bankBatchName.value.trim(),
  };

  if (newQ.value.type === 'multiple_choice') {
    payload.choices = newQ.value.choices;
    payload.correct_answer = newQ.value.choices[newQ.value.correctIdx];
  } else if (newQ.value.type === 'identification') {
    // correct_answer is the expected answer (optional)
    if (newQ.value.correctAnswer.trim()) {
      payload.correct_answer = newQ.value.correctAnswer.trim();
    }
    payload.case_sensitive = newQ.value.caseSensitive;
  } else if (newQ.value.type === 'enumeration') {
    // Store expected items as newline-separated in correct_answer
    const items = newQ.value.enumerationItems.filter(i => i.trim());
    payload.correct_answer = items.join('\n');
    payload.points = newQ.value.points ? parseInt(newQ.value.points) : items.length;
    payload.case_sensitive = newQ.value.caseSensitive;
  }
  // essay: no extra fields

  bankSaving.value = true;
  message.value = "";
  error.value = "";
  try {
    await apiClient.post(`/api/instructor/subjects/${selectedSubjectId.value}/question-bank/`, payload);
    showSuccess('Question saved', 'The question is ready to use in exams for this course.');
    newQ.value = { type: newQ.value.type, text: '', choices: ['', '', '', ''], correctIdx: 0, enumerationItems: ['', '', ''], points: '', correctAnswer: '', caseSensitive: newQ.value.caseSensitive };
    await fetchQuestionBank();
  } catch (err) {
    error.value = err?.response?.data?.error || 'Failed to save question.';
  } finally {
    bankSaving.value = false;
  }
}

function requestDeleteBankQuestion(item) {
  openConfirm({
    title: 'Delete bank question?',
    message: 'This removes the question from the course bank. Exams that already use a copy will keep it.',
    confirmText: 'Delete question',
    variant: 'danger',
    onConfirm: async () => {
      bankSaving.value = true;
      try {
        await apiClient.delete(`/api/instructor/subjects/${selectedSubjectId.value}/question-bank/${item.id}/`);
        await fetchQuestionBank();
        selectedBankQuestionIds.value = selectedBankQuestionIds.value.filter(id => id !== item.id);
        showSuccess('Question deleted', 'The question was removed from this course bank.');
      } catch (err) {
        error.value = err?.response?.data?.error || 'Unable to delete bank question.';
      } finally {
        bankSaving.value = false;
      }
    },
  });
}

function requestDeleteBankBatch(batch) {
  const totalQuestions = bankBatches.value.find(item => item.id === batch.id)?.questions.length || batch.questions.length;
  openConfirm({
    title: 'Delete this question batch?',
    message: `This removes all ${totalQuestions} question(s) in the batch from the course bank. Exams that already use copies will keep them.`,
    confirmText: 'Delete batch',
    variant: 'danger',
    onConfirm: async () => {
      bankSaving.value = true;
      try {
        await apiClient.delete(`/api/instructor/subjects/${selectedSubjectId.value}/question-bank/batches/${batch.id}/`);
        await fetchQuestionBank();
        selectedBankQuestionIds.value = selectedBankQuestionIds.value.filter(id => bankQuestions.value.some(item => item.id === id));
        showSuccess('Batch deleted', 'The question batch was removed from this course bank.');
      } catch (err) {
        error.value = err?.response?.data?.error || 'Unable to delete question batch.';
      } finally {
        bankSaving.value = false;
      }
    },
  });
}

async function addSelectedBankQuestions() {
  if (!managingExam.value || !selectedSubjectId.value || !selectedBankQuestionIds.value.length || bankSaving.value) return;
  bankSaving.value = true;
  error.value = '';
  try {
    const { data } = await apiClient.post(
      `/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/${managingExam.value.id}/questions/from-bank/`,
      { question_ids: selectedBankQuestionIds.value },
    );
    selectedBankQuestionIds.value = [];
    await fetchExamQuestions();
    showSuccess('Exam updated', `${data.added_count} question(s) added from the course bank.`);
  } catch (err) {
    error.value = err?.response?.data?.error || 'Unable to add selected questions.';
  } finally {
    bankSaving.value = false;
  }
}

async function deleteExamQuestion(questionId) {
  if (!managingExam.value || !selectedSubjectId.value || examIsFinal.value) return;
  message.value = "";
  error.value = "";
  try {
    await apiClient.delete(`/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/${managingExam.value.id}/questions/${questionId}/`);
    showSuccess('Question deleted', 'The question was removed from the exam.');
    await fetchExamQuestions();
  } catch (err) {
    error.value = "Failed to delete question.";
  }
}

function onAikenFileUpload(event) {
  const file = event.target?.files?.[0];
  if (!file) return;
  aikenFileName.value = file.name;
  const reader = new FileReader();
  reader.onload = (e) => {
    bulkText.value = e.target.result;
  };
  reader.readAsText(file);
}

async function processBulkQuestions() {
  if (!bulkText.value.trim() || !selectedSubjectId.value) return;
  bankSaving.value = true;
  message.value = "";
  error.value = "";
  try {
    const response = await apiClient.post(`/api/instructor/subjects/${selectedSubjectId.value}/question-bank/`, {
      bulk_text: bulkText.value,
      question_file_format: bankImportFormat.value,
      batch_name: bankImportBatchName.value.trim() || aikenFileName.value || 'Question import',
    });
    bulkText.value = "";
    aikenFileName.value = "";
    bankImportBatchName.value = '';
    showSuccess('Questions imported', `${response.data.created_count} question(s) were added to this course's bank.`);
    await fetchQuestionBank();
  } catch (err) {
    error.value = err.response?.data?.error || 'Could not import questions.';
  } finally {
    bankSaving.value = false;
  }
}

async function finalizeExam() {
  if (!managingExam.value || !selectedSubjectId.value) return;
  questionsLoading.value = true;
  message.value = "";
  error.value = "";
  try {
    await apiClient.post(`/api/instructor/subjects/${selectedSubjectId.value}/exam-sets/${managingExam.value.id}/finalize/`);
    showSuccess('Exam published', 'Students can now see the exam on their dashboard.');
    examIsFinal.value = true;
    await fetchExamQuestions();
    await fetchExamSets();
    await fetchUpcomingExams();
  } catch (err) {
    error.value = err?.response?.data?.error || "Failed to finalize exam.";
  } finally {
    questionsLoading.value = false;
  }
}

function getExamineeReportStatus(ex) {
  if (ex.status === 'Done' || ex.status === 'Terminated') return ex.status;
  if (statsExam.value?.due_at && new Date() > new Date(statsExam.value.due_at)) {
    return 'Not Taken';
  }
  return ex.status === 'In Progress' ? 'Ongoing' : 'Pending';
}

function submissionStatus(row) {
  if (row.terminated) return 'Terminated';
  if (row.is_done) return 'Done';
  if (row.due_at && new Date(row.due_at).getTime() < Date.now()) return 'Not Taken';
  return row.started_at ? 'Ongoing' : 'Pending';
}

function submissionStatusClass(row) {
  return {
    Terminated: 'badge-terminated',
    Done: 'badge-done',
    'Not Taken': 'badge-not-taken',
    Ongoing: 'badge-active',
    Pending: 'badge-pending',
  }[submissionStatus(row)];
}

async function fetchStatsData(exam, isBackground = false) {
  const generation = ++statsFetchGeneration;
  try {
    const { data } = await apiClient.get(`/api/instructor/subjects/${exam.subject_id}/exam-sets/${exam.id}/stats/`);
    const examinees = await attachStatsSnapshotUrls(data.examinees || []);
    if (generation !== statsFetchGeneration || statsExam.value?.id !== exam.id) return;
    const activeSources = new Set(examinees.map(row => row.snapshot_url).filter(Boolean));
    releaseStatsSnapshotUrls(activeSources);
    examStatsSets.value = data.sets || [];
    examStatsExaminees.value = examinees;
  } catch(err) {
    if (!isBackground) error.value = "Unable to load exam statistics.";
  }
}

async function openExamStats(exam) {
  const targetSub = subjects.value.find(s => s.id === (exam.subject_id || selectedSubjectId.value));
  const enrichedExam = {
    ...exam,
    subject_id: exam.subject_id || selectedSubjectId.value,
    subject_code: exam.subject_code || targetSub?.code || '',
    subject_name: exam.subject_name || targetSub?.name || '',
  };
  statsExam.value = enrichedExam;
  statsLoading.value = true;
  examStatsSets.value = [];
  examStatsExaminees.value = [];
  
  await fetchStatsData(enrichedExam);
  statsLoading.value = false;

  if (statsPollInterval) clearInterval(statsPollInterval);
  statsPollInterval = setInterval(() => {
    if (statsExam.value && statsExam.value.id === enrichedExam.id) {
      fetchStatsData(enrichedExam, true);
    } else {
      clearInterval(statsPollInterval);
    }
  }, 5000);
}

function closeExamStats() {
  statsFetchGeneration += 1;
  releaseStatsSnapshotUrls();
  statsExam.value = null;
  examStatsSets.value = [];
  examStatsExaminees.value = [];
  if (statsPollInterval) {
    clearInterval(statsPollInterval);
    statsPollInterval = null;
  }
}

async function refreshSetsView() {
  await fetchSubjectSets();
  if (selectedSubjectSetId.value) {
    await fetchSubjectStudents();
  } else {
    subjectStudents.value = [];
  }
}

watch(activeNav, async () => {
  if (activeNav.value === "dashboard") {
    if (!upcomingLoaded.value) await fetchUpcomingExams();
  }
  if (activeNav.value === "courses") {
    if (!subjectsLoaded.value) await fetchSubjects();
    if (selectedSubjectId.value) {
      if (activeCourseTab.value === "uploaded-exams") {
        if (!examSetsLoaded.value) await fetchExamSets();
        if (!subjectSetsLoaded.value) await fetchSubjectSets();
      }
      if (activeCourseTab.value === "sets") {
        if (!subjectSetsLoaded.value) await refreshSetsView();
      }
      if (activeCourseTab.value === "exam-progress") {
        if (!examProgressLoaded.value) await fetchExamProgress();
      }
      if (activeCourseTab.value === "question-bank") await fetchQuestionBank();
    }
  }
});

watch(selectedSubjectId, () => {
  if (selectedCourse.value) {
    courseAnnouncement.value = selectedCourse.value.announcements || "";
  }
});

watch(
  () => route.params.courseId,
  async () => {
    syncSelectedCourseFromRoute();
    if (!selectedSubjectId.value) return;
    if (activeCourseTab.value === "uploaded-exams") {
      await fetchExamSets();
      await fetchSubjectSets();
    }
    if (activeCourseTab.value === "sets") await refreshSetsView();
    if (activeCourseTab.value === "exam-progress") await fetchExamProgress();
    if (activeCourseTab.value === "question-bank") await fetchQuestionBank();
  },
  { immediate: true },
);

watch(
  () => route.params.setId,
  async () => {
    syncSelectedCourseFromRoute();
    if (activeCourseTab.value === "sets") {
      await refreshSetsView();
    }
  },
);

watch(selectedSubjectId, async () => {
  selectedSubjectSetId.value = "";
  subjectStudents.value = [];
  bulkEnrollResult.value = null;
  // Reset per-subject cache flags whenever the course changes
  examSetsLoaded.value = false;
  subjectSetsLoaded.value = false;
  examProgressLoaded.value = false;
  bankQuestions.value = [];
  bankBatches.value = [];
  selectedBankQuestionIds.value = [];
  if (!selectedSubjectId.value) {
    examSets.value = [];
    subjectSets.value = [];
    examProgressRows.value = [];
    return;
  }
  if (activeCourseTab.value === "uploaded-exams") {
    await fetchExamSets();
    await fetchSubjectSets();
  }
  if (activeCourseTab.value === "sets") await refreshSetsView();
  if (activeCourseTab.value === "exam-progress") await fetchExamProgress();
  if (activeCourseTab.value === "question-bank") await fetchQuestionBank();
});

watch(activeCourseTab, async () => {
  if (!selectedSubjectId.value) return;
  if (activeCourseTab.value === "uploaded-exams") {
    if (!examSetsLoaded.value) await fetchExamSets();
    if (!subjectSetsLoaded.value) await fetchSubjectSets();
  }
  if (activeCourseTab.value === "sets") {
    await refreshSetsView();
  }
  if (activeCourseTab.value === "exam-progress") {
    if (!examProgressLoaded.value) await fetchExamProgress();
  }
  if (activeCourseTab.value === "question-bank") await fetchQuestionBank();
});

watch(progressSets, (sets) => {
  if (!sets.length) {
    selectedProgressSetId.value = null;
    return;
  }
  if (!sets.some((s) => s.id === selectedProgressSetId.value)) {
    selectedProgressSetId.value = sets[0].id;
    selectedProgressStudentEmail.value = "";
  }
});

watch(progressView, (view) => {
  if (view === "student" && !progressSort.value.startsWith("student_")) {
    progressSort.value = "student_asc";
  }
});

watch(progressExamsForSelectedSet, (exams) => {
  if (!exams.length) {
    selectedProgressExamId.value = null;
    return;
  }
  if (!exams.some((exam) => exam.id === selectedProgressExamId.value)) {
    selectedProgressExamId.value = exams[0].id;
  }
});

onMounted(async () => {
  updateTime();
  timeInterval = setInterval(updateTime, 1000);
  if (!subjectsLoaded.value) await fetchSubjects();
  if (activeNav.value === "dashboard" && !upcomingLoaded.value) {
    await fetchUpcomingExams();
  }
});

</script>

<style scoped>
@import '@/assets/dashboard.css';


/* Premium Proctoring Toggle UI */
.premium-toggle-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}
.premium-toggle-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  transform: translateY(-1px);
}
.premium-toggle-card--locked {
  cursor: not-allowed;
  background: #f8fafc;
}
.premium-toggle-card--locked:hover {
  border-color: #e2e8f0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
  transform: none;
}
.premium-toggle-card--locked .premium-slider {
  cursor: not-allowed;
  opacity: 0.72;
}
.ptc-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ptc-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.ptc-title {
  font-weight: 700;
  font-size: 0.95rem;
  color: #1e293b;
}
.ptc-desc {
  font-size: 0.75rem;
  color: #64748b;
}

/* Apple-style Toggle Switch */
.premium-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}
.premium-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.premium-slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #cbd5e1;
  transition: .3s cubic-bezier(0.4, 0.0, 0.2, 1);
  border-radius: 24px;
}
.premium-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .3s cubic-bezier(0.4, 0.0, 0.2, 1);
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.premium-switch input:checked + .premium-slider {
  background-color: #059669;
}
.premium-switch input:focus + .premium-slider {
  box-shadow: 0 0 1px #059669;
}
.premium-switch input:checked + .premium-slider:before {
  transform: translateX(20px);
}

/* Ã¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢Â
   EXAM STATS MODAL Ã¢â‚¬" Premium Redesign
Ã¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢ÂÃ¢"¢Â */

/* Transition */
.stats-fade-enter-active,
.stats-fade-leave-active { transition: opacity 0.25s ease; }
.stats-fade-enter-from,
.stats-fade-leave-to { opacity: 0; }
.stats-fade-enter-active .stats-shell,
.stats-fade-leave-active .stats-shell { transition: transform 0.28s cubic-bezier(0.34,1.26,0.64,1), opacity 0.25s ease; }
.stats-fade-enter-from .stats-shell,
.stats-fade-leave-to .stats-shell { transform: scale(0.94) translateY(16px); opacity: 0; }

/* Backdrop */
.stats-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.58);
  backdrop-filter: blur(7px);
}

/* Modal shell */
.stats-shell {
  width: 100%;
  max-width: 1200px;
  background: #fff;
  border: 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.32);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 3rem);
}

/* Header */
.stats-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.8rem 2rem;
  background: linear-gradient(120deg, #1d3461, #314d83);
  color: #fff;
}
.stats-header-content { flex: 1; min-width: 0; }
.stats-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: #c9d8f1;
  margin-bottom: 0.5rem;
}
.stats-title {
  margin: 0;
  font-size: clamp(1.45rem, 2.1vw, 1.85rem);
  font-weight: 800;
  font-family: 'Poppins', sans-serif;
  letter-spacing: -0.01em;
  line-height: 1.2;
}
.stats-course-label {
  display: inline-flex;
  margin: 0.55rem 0 0;
  font-size: 0.98rem;
  color: #dce7fa;
}
.stats-close-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: rgba(255,255,255,.12);
  border: 0;
  color: #fff;
  cursor: pointer;
  transition: background 0.18s;
  padding: 0;
}
.stats-close-btn:hover { background: rgba(255,255,255,.22); }

/* Summary bar */
.stats-summary-bar {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  padding: 1.5rem 2rem;
  background: #f7f9fc;
  border-bottom: 1px solid #e2e8f0;
}
.stats-summary-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 1.25rem 1.4rem;
  background: #ffffff;
  border: 0;
  border-radius: 8px;
  gap: 0.45rem;
  box-shadow: 0 2px 8px rgba(29,52,97,.06);
}
.stats-summary-pill--green { background: #f0faf5; }
.stats-summary-pill--amber { background: #fff9ec; }
.ssp-num {
  font-size: 2.15rem;
  font-weight: 800;
  color: #1d3461;
  line-height: 1;
}
.ssp-lbl {
  font-size: 0.88rem;
  color: #64748b;
  font-weight: 700;
}
.stats-summary-pill--green .ssp-num { color: #059669; }
.stats-summary-pill--amber .ssp-num { color: #d97706; }

/* Body */
.stats-body { padding: 0 2rem 2rem; overflow-y: auto; flex: 1; background: #f7f9fc; }
.stats-loading-state {
  display: grid;
  gap: 0.5rem;
  padding: 1.5rem 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
.stats-empty {
  text-align: center;
  color: #94a3b8;
  padding: 3rem 0;
  font-size: 0.95rem;
  margin: 0;
}

/* ================================================
   PROCTORING / INTEGRITY REPORT — Slide Drawer
================================================ */

/* Transition */
/* ---- Slide transition ---- */
.ir-slide-enter-active, .ir-slide-leave-active { transition: opacity 0.28s ease; }
.ir-slide-enter-from, .ir-slide-leave-to { opacity: 0; }
.ir-slide-enter-active .ir-drawer, .ir-slide-leave-active .ir-drawer { transition: transform 0.32s cubic-bezier(0.32,0.72,0,1), opacity 0.28s ease; }
.ir-slide-enter-from .ir-drawer, .ir-slide-leave-to .ir-drawer { transform: translateX(100%); opacity: 0; }

/* ---- Backdrop ---- */
.ir-backdrop {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(6px);
  display: flex; align-items: stretch; justify-content: flex-end;
}

/* ---- Drawer shell ---- */
.ir-drawer {
  width: 100%; max-width: 780px;
  background: #f8fafc;
  display: flex; flex-direction: column; overflow: hidden;
  box-shadow: -8px 0 48px rgba(15,23,42,0.14);
  border-left: 1px solid #e2e8f0;
}

/* ---- Header ---- */
.ir-drawer-header {
  position: relative; flex-shrink: 0; overflow: hidden;
  display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;
  padding: 1.35rem 1.75rem;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  border-left: 4px solid #1D3461;
}
.ir-dh-glow { display: none; }
.ir-dh-glow--r { display: none; }
.ir-dh-content { flex: 1; min-width: 0; position: relative; z-index: 1; }
.ir-dh-eyebrow {
  display: inline-flex; align-items: center; gap: 0.4rem;
  font-size: 0.63rem; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.15em; color: #1D3461; margin-bottom: 0.35rem;
}
.ir-dh-title {
  margin: 0; font-size: 1.25rem; font-weight: 800;
  font-family: 'Poppins', sans-serif; color: #1e293b;
  letter-spacing: -0.02em; line-height: 1.2;
}
.ir-dh-meta { display: flex; flex-wrap: wrap; gap: 0.45rem 0.75rem; margin-top: 0.5rem; }
.ir-dh-email {
  display: inline-flex; align-items: center; gap: 0.3rem;
  font-size: 0.8rem; color: #64748b; font-weight: 500;
}
.ir-dh-attempt {
  font-size: 0.7rem; font-weight: 700;
  background: #e6eaf2; border: 1px solid #c5cedf;
  color: #162a4f; padding: 0.1rem 0.55rem; border-radius: 999px;
}
.ir-dh-close {
  flex-shrink: 0; position: relative; z-index: 1;
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 8px;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  color: #64748b; cursor: pointer; transition: all 0.2s; padding: 0;
}
.ir-dh-close:hover { background: #fee2e2; border-color: #fca5a5; color: #dc2626; }

/* ---- Loading / error ---- */
.ir-state {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 0.75rem; padding: 3rem;
  color: #94a3b8; text-align: center;
}
.ir-state-error { color: #dc2626; }
.ir-spinner {
  width: 34px; height: 34px;
  border: 3px solid #e2e8f0; border-top-color: #6366f1;
  border-radius: 50%; animation: spin 0.85s linear infinite;
}

/* ---- Hero section ---- */
.ir-hero {
  display: flex; align-items: center; gap: 1.75rem;
  padding: 1.4rem 1.75rem 1.35rem;
  background: #ffffff; flex-shrink: 0;
  border-bottom: 1px solid #e9eaf4;
}

/* SVG ring dial */
.ir-dial { position: relative; flex-shrink: 0; width: 96px; height: 96px; }
.ir-dial-svg { width: 96px; height: 96px; }
.ir-dial-track { stroke: #e9eaf4; }
.ir-dial-fill { stroke: var(--dial-stroke, #6366f1); transition: stroke-dashoffset 0.55s cubic-bezier(0.4,0,0.2,1); }
.ir-dial-inner {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.ir-dial-val {
  font-size: 1.6rem; font-weight: 900; line-height: 1;
  color: var(--dial-text, #0f172a); font-family: 'Poppins', sans-serif;
  letter-spacing: -0.03em;
}
.ir-dial-unit { font-size: 0.7rem; font-weight: 700; color: var(--dial-text, #64748b); line-height: 1; margin-top: 1px; }
.ir-dial-lbl { font-size: 0.5rem; text-transform: uppercase; letter-spacing: 0.12em; color: #94a3b8; margin-top: 3px; }
.ir-tone-good    { --dial-stroke: #10b981; --dial-text: #047857; }
.ir-tone-warn    { --dial-stroke: #f59e0b; --dial-text: #b45309; }
.ir-tone-bad     { --dial-stroke: #ef4444; --dial-text: #b91c1c; }
.ir-tone-neutral { --dial-stroke: #cbd5e1; --dial-text: #64748b; }

/* Hero right: 2-row layout */
.ir-hero-right {
  flex: 1; min-width: 0; display: flex; flex-direction: column;
  gap: 0; border-left: 1px solid #e9eaf4; padding-left: 1.6rem;
}

/* Top row: score + divider + status */
.ir-top-row {
  display: flex; align-items: center; gap: 0;
  padding-bottom: 1rem; border-bottom: 1px solid #f1f5f9;
}
.ir-score-block { display: flex; flex-direction: column; padding-right: 1.25rem; }
.ir-score-num {
  font-size: 2rem; font-weight: 900; color: #0f172a;
  font-family: 'Poppins', sans-serif; line-height: 1; letter-spacing: -0.04em;
}
.ir-score-lbl {
  font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.1em;
  color: #94a3b8; font-weight: 600; margin-top: 3px;
}
.ir-top-divider {
  width: 1px; height: 36px; background: #e2e8f0; margin: 0 1.25rem;
}
.ir-status-block { display: flex; align-items: center; }
.ir-status-chip {
  display: inline-flex; align-items: center; gap: 0.4rem;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.03em;
  padding: 0.35rem 0.85rem; border-radius: 6px;
}
.ir-chip-done       { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
.ir-chip-terminated { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.ir-chip-pending    { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }

/* Bottom row: 4 stat metrics with dividers */
.ir-metrics-row {
  display: flex; align-items: stretch; padding-top: 1rem;
}
.ir-metric {
  flex: 1; display: flex; flex-direction: column; gap: 3px; padding: 0 1rem;
}
.ir-metric:first-child { padding-left: 0; }
.ir-metric-num {
  font-size: 1.35rem; font-weight: 800; color: #475569;
  font-family: 'Poppins', sans-serif; line-height: 1; letter-spacing: -0.02em;
}
.ir-metric-lbl {
  font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em;
  color: #94a3b8; font-weight: 600;
}
.ir-metric-warn .ir-metric-num  { color: #d97706; }
.ir-metric-warn .ir-metric-lbl  { color: #b45309; }
.ir-metric-danger .ir-metric-num { color: #dc2626; }
.ir-metric-danger .ir-metric-lbl { color: #b91c1c; }
.ir-metric-sep {
  width: 1px; background: #e9eaf4; flex-shrink: 0; margin: 0 0.15rem;
}

/* ---- Tab bar ---- */
.ir-tab-bar {
  display: flex; background: #ffffff; flex-shrink: 0;
  border-bottom: 2px solid #e9eaf4; padding: 0 1.75rem;
}
.ir-tab-btn {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.8rem 0.9rem 0.7rem;
  font-size: 0.82rem; font-weight: 700; letter-spacing: 0.01em;
  color: #94a3b8; background: none; border: none;
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  cursor: pointer; transition: color 0.18s, border-color 0.18s;
  font-family: 'Poppins', sans-serif;
}
.ir-tab-btn:hover { color: #4338ca; }
.ir-tab-btn--active { color: #4338ca; border-bottom-color: #6366f1; }
.ir-tab-count {
  display: inline-flex; align-items: center; justify-content: center;
  background: #e0e7ff; color: #4338ca;
  font-size: 0.62rem; font-weight: 800;
  min-width: 17px; height: 17px; padding: 0 0.28rem; border-radius: 999px;
}
.ir-tab-count--done { background: #dcfce7; color: #047857; }

/* ---- Tab panel ---- */
.ir-tab-panel {
  flex: 1; overflow-y: auto; padding: 1.25rem 1.75rem 2rem;
  background: #f8fafc;
}
.ir-tab-panel::-webkit-scrollbar { width: 5px; }
.ir-tab-panel::-webkit-scrollbar-track { background: transparent; }
.ir-tab-panel::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 5px; }

/* ---- Log list ---- */
.ir-log-list { display: flex; flex-direction: column; gap: 0.45rem; }
.ir-log-row {
  display: flex; align-items: flex-start; gap: 0.75rem;
  background: #ffffff; border: 1px solid #e9eaf4;
  border-radius: 12px; padding: 0.85rem 1rem; position: relative; overflow: hidden;
  transition: box-shadow 0.18s;
}
.ir-log-row:hover { box-shadow: 0 2px 12px rgba(99,102,241,0.08); }
.ir-log-bar {
  position: absolute; left: 0; top: 0; bottom: 0;
  width: 3px; background: #e2e8f0; border-radius: 3px 0 0 3px;
}
.ir-log--critical { background: #fff5f5; border-color: #fecdd3; }
.ir-log--critical .ir-log-bar { background: #ef4444; }
.ir-log--warning  { background: #fffbeb; border-color: #fde68a; }
.ir-log--warning  .ir-log-bar { background: #f59e0b; }

.ir-log-icon {
  flex-shrink: 0; width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  background: #f1f5f9; color: #94a3b8; margin-top: 0.05rem;
}
.ir-log--critical .ir-log-icon { background: #fee2e2; color: #dc2626; }
.ir-log--warning  .ir-log-icon { background: #fef3c7; color: #d97706; }

.ir-log-body { flex: 1; min-width: 0; }
.ir-log-top { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.25rem; }
.ir-log-type {
  font-weight: 700; font-size: 0.86rem; color: #0f172a;
  font-family: 'Poppins', sans-serif;
}
.ir-log-time { margin-left: auto; font-size: 0.68rem; color: #94a3b8; white-space: nowrap; }
.ir-log-msg { margin: 0; font-size: 0.8rem; color: #64748b; line-height: 1.5; }

/* Severity badge */
.ir-sev-badge {
  font-size: 0.6rem; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.05em; padding: 0.1rem 0.4rem; border-radius: 4px;
}
.ir-sev-critical { background: #fee2e2; color: #b91c1c; }
.ir-sev-warning  { background: #fef3c7; color: #b45309; }
.ir-sev-info     { background: #e0f2fe; color: #0369a1; }
.ir-sev-neutral  { background: #f1f5f9; color: #64748b; }

/* ---- Evidence gallery ---- */
.ir-gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
  gap: 0.85rem;
}
.ir-thumb {
  display: block; text-decoration: none; color: inherit;
  border-radius: 12px; overflow: hidden;
  border: 1px solid #e2e8f0; background: #ffffff;
  transition: box-shadow 0.22s, transform 0.22s, border-color 0.22s;
}
.ir-thumb:hover {
  box-shadow: 0 8px 24px rgba(99,102,241,0.15);
  transform: translateY(-3px); border-color: #a5b4fc;
}
.ir-thumb-img-wrap { position: relative; overflow: hidden; }
.ir-thumb-img-wrap img {
  width: 100%; aspect-ratio: 4/3; object-fit: cover;
  display: block; background: #f1f5f9; transition: transform 0.3s;
}
.ir-thumb:hover .ir-thumb-img-wrap img { transform: scale(1.05); }
.ir-thumb-overlay {
  position: absolute; inset: 0;
  background: rgba(15,23,42,0.5);
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.22s;
}
.ir-thumb:hover .ir-thumb-overlay { opacity: 1; }
.ir-thumb-missing {
  min-height: 105px; display: flex; align-items: center; justify-content: center;
  background: #f1f5f9; color: #94a3b8; font-size: 0.75rem;
}
.ir-thumb-cap { padding: 0.5rem 0.65rem 0.6rem; background: #fff; }
.ir-thumb-badge {
  display: inline-block; font-size: 0.58rem; font-weight: 800; text-transform: uppercase;
  background: #e0e7ff; color: #4338ca;
  padding: 0.08rem 0.38rem; border-radius: 4px; margin-bottom: 0.2rem;
}
.ir-thumb-caption { display: block; font-size: 0.68rem; color: #64748b; line-height: 1.35; }
.ir-thumb-time { display: block; margin-top: 0.25rem; font-size: 0.62rem; color: #94a3b8; line-height: 1.3; }

/* ---- Empty state ---- */
.ir-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.65rem; padding: 3rem 0; color: #94a3b8;
  text-align: center; font-size: 0.88rem;
}
.ir-empty p { margin: 0; }

/* ---- Subjective-answer grading ---- */
.ir-grading-list { display: flex; flex-direction: column; gap: 0.85rem; }
.ir-grading-summary {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: 0.9rem 1rem; border: 1px solid #fde68a; border-radius: 12px;
  background: #fffbeb; color: #92400e;
}
.ir-grading-summary--done { border-color: #a7f3d0; background: #ecfdf5; color: #065f46; }
.ir-grading-summary strong { display: block; font-size: 0.88rem; }
.ir-grading-summary p { margin: 0.2rem 0 0; font-size: 0.75rem; line-height: 1.4; }
.ir-grading-summary > span { flex-shrink: 0; font-size: 0.72rem; font-weight: 800; }
.ir-review-checked {
  align-self: flex-start; border: 1px solid #c6d5ed; border-radius: 9px;
  background: #fff; color: #1d3461; padding: 0.6rem 0.85rem;
  font: inherit; font-size: 0.78rem; font-weight: 800; cursor: pointer;
}
.ir-review-checked:hover, .ir-review-checked:focus-visible { background: #edf3fd; border-color: #7799ce; }
.ir-checked-empty {
  display: flex; flex-direction: column; align-items: center; gap: 0.35rem;
  padding: 2.5rem 1.25rem; border: 1px solid #d4eddf; border-radius: 14px;
  background: #fff; color: #065f46; text-align: center;
}
.ir-checked-empty-icon { display: grid; place-items: center; width: 48px; height: 48px; margin-bottom: 0.35rem; border-radius: 50%; background: #dcfce7; font-size: 1.4rem; font-weight: 800; }
.ir-checked-empty strong { font-size: 1.05rem; }
.ir-checked-empty p { max-width: 46ch; margin: 0; color: #475569; font-size: 0.82rem; line-height: 1.5; }
.ir-answer-card {
  padding: 1rem; border: 1px solid #e2e8f0; border-radius: 12px;
  background: #fff;
}
.ir-answer-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.ir-answer-number {
  font-size: 0.66rem; font-weight: 800; color: #6366f1;
  text-transform: uppercase; letter-spacing: 0.08em;
}
.ir-answer-card h4 { margin: 0.65rem 0; color: #0f172a; font-size: 0.92rem; line-height: 1.45; }
.ir-points-field { display: flex; align-items: center; gap: 0.4rem; color: #64748b; font-size: 0.72rem; font-weight: 700; }
.ir-points-field input {
  width: 70px; padding: 0.38rem 0.45rem; border: 1px solid #cbd5e1;
  border-radius: 7px; color: #0f172a; font: inherit; text-align: right;
}
.ir-points-field input:focus { outline: 2px solid #c7d2fe; border-color: #6366f1; }
.ir-student-answer { padding: 0.8rem; border-radius: 9px; background: #f8fafc; border: 1px solid #eef2f7; }
.ir-student-answer > span { font-size: 0.62rem; font-weight: 800; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; }
.ir-student-answer p { margin: 0.4rem 0 0; color: #334155; font-size: 0.86rem; line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }
.ir-grading-actions { display: flex; align-items: center; justify-content: flex-end; gap: 1rem; position: sticky; bottom: 0; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(255,255,255,0.96); }
.ir-grading-actions p { flex: 1; margin: 0; font-size: 0.76rem; }
.ir-grading-error { color: #dc2626; }
.ep-report-btn--grade { background: #fff7ed; border-color: #fdba74; color: #c2410c; }
.ep-report-btn--grade:hover { background: #ffedd5; border-color: #fb923c; color: #9a3412; }

@media (max-width: 640px) {
  .ir-grading-summary, .ir-answer-heading { align-items: flex-start; flex-direction: column; }
  .ir-points-field { align-self: stretch; justify-content: flex-end; }
}

/* ---- Instructor-specific (unchanged) ---- */
.q-list { display: flex; flex-direction: column; gap: 0.85rem; }
.q-card { background: #fff; border: 1px solid #e8eaed; border-radius: 14px; padding: 1.15rem; transition: border-color 0.2s; }
.q-card:hover { border-color: #00a699; }
.q-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
.q-text { margin: 0 0 1rem; color: #0f0f0f; font-size: 1rem; font-weight: 600; }
.q-choices-list { list-style: disc; padding-left: 1.5rem; margin: 0; color: #374151; font-size: 0.92rem; }
.correct-choice { color: #059669; font-weight: 700; }
.choices-editor h5 { margin: 0 0 0.5rem; color: #6b7280; font-size: 0.85rem; }
.choice-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.badge-neutral { background: #f3f4f6; color: #6b7280; font-size: 0.72rem; padding: 2px 8px; border-radius: 5px; font-weight: 600; }
.enroll-grid { display: grid; grid-template-columns: 1fr 1.5fr; gap: 1rem; margin-bottom: 2rem; }
.data-table tr.gaze-event-row td { background: #fef3c7; }
.data-table tr.gaze-event-row td:first-child { border-left: 3px solid #f59e0b; }

/* ---- Examinees stats table ---- */
.stats-examinees-section {
  margin-top: 0;
  padding: 1.5rem;
  background: #ffffff;
  border: 0;
  border-radius: 10px;
  box-shadow: 0 6px 22px rgba(29, 52, 97, 0.05);
}
.stats-examinees-heading { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-bottom: 1.15rem; }
.stats-live-label { display: inline-flex; align-items: center; gap: .45rem; color: #15803d; font-size: .82rem; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; }
.stats-live-dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 4px #dcfce7; }
.stats-refresh-note { color: #64748b; font-size: .82rem; }
.stats-examinees-title {
  font-size: 1.45rem;
  font-weight: 800;
  color: #1d3461;
  margin: .3rem 0 0;
}
.stats-table-wrapper {
  overflow: auto;
  border: 0;
  border-radius: 8px;
  background: #ffffff;
}
.stats-table { width: 100%; min-width: 830px; border-collapse: collapse; font-size: 0.95rem; text-align: left; }
.stats-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f1f5fb;
  padding: 1rem;
  font-size: 0.78rem;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #cbd5e1;
  white-space: nowrap;
}
.stats-table td { padding: 1rem; border-bottom: 1px solid #e8edf4; color: #334155; vertical-align: middle; }
.stats-table tbody tr { transition: background 0.15s ease; }
.stats-table tbody tr:hover { background: #f8fafc; }
.stats-table tr:last-child td { border-bottom: none; }
.stats-ex-name { font-weight: 800; color: #1d3461; margin-bottom: 0.2rem; }
.stats-ex-email { font-size: 0.8rem; color: #64748b; }
.stats-center { text-align: center !important; }
.stats-warn-text { color: #ef4444; font-weight: 700; }
.stats-activity { display: flex; flex-direction: column; gap: .25rem; font-size: .88rem; white-space: nowrap; }
.stats-table-empty { text-align: center; padding: 2.25rem !important; color: #64748b !important; }
.stats-badge { display: inline-flex; padding: 0.38rem 0.7rem; border-radius: 8px; font-size: 0.83rem; font-weight: 700; white-space: nowrap; border: 1px solid transparent; }
.stats-badge--green { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
.stats-badge--blue { background: #e8f1ff; color: #2458d6; border-color: #bfdbfe; }
.stats-badge--amber { background: #fffbeb; color: #b45309; border-color: #fde68a; }
.stats-badge--orange { background: #fff0df; color: #9a3412; border-color: #fed7aa; }
.stats-badge--red { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
.stats-badge--gray { background: #f8fafc; color: #64748b; border-color: #e2e8f0; }
.stats-badge--neutral { background: #f8fafc; color: #475569; border-color: #e2e8f0; }
.stats-report-btn {
  padding: 0.55rem 0.85rem;
  border-radius: 9px;
  border: 1px solid #c6d5ed;
  background: #ffffff;
  color: #1d3461;
  font-size: 0.83rem;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.stats-report-btn:hover { background: #edf3fd; border-color: #7799ce; }

/* ---- Snapshot column ---- */
.stats-snapshot-wrapper { width: 96px; height: 64px; border-radius: 8px; overflow: hidden; background: #f1f5f9; border: 1px solid #dbe3ee; display: flex; align-items: center; justify-content: center; margin: 0 auto; }
.stats-snapshot-img { width: 100%; height: 100%; object-fit: cover; }
.stats-snapshot-placeholder { color: #cbd5e1; display: flex; }

.archive-heading { display: flex; align-items: center; justify-content: space-between; gap: 1.25rem; }
.archive-heading h2 { margin: 0 0 .2rem; color: #1d3461; font: 750 1.1rem 'Poppins', sans-serif; }
.archive-heading p { margin: 0; color: #718098; font-size: .8rem; }
.archive-heading > span { flex: none; color: #61728c; font-size: .75rem; font-weight: 700; }
.archive-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
.archive-course-card { display: flex; flex-direction: column; align-items: flex-start; min-height: 190px; padding: 1.3rem; border: 1px solid #dce4ee; border-radius: 15px; background: #fff; box-shadow: 0 8px 24px rgba(18, 39, 73, .04); }
.archive-course-card__code { color: #617898; font-size: .7rem; font-weight: 800; letter-spacing: .07em; }
.archive-course-card h3 { margin: .45rem 0 .2rem; color: #1d3461; font: 750 1rem 'Poppins', sans-serif; }
.archive-course-card p { margin: 0 0 1.2rem; color: #718098; font-size: .78rem; }
.archive-course-card__restore { margin-top: auto; padding: .6rem .9rem; border: 1px solid #c7d5e7; border-radius: 9px; background: #f6f8fc; color: #1d3461; font: 700 .76rem 'Poppins', sans-serif; cursor: pointer; }
.archive-course-card__restore:hover:not(:disabled) { background: #eaf0f9; }
.archive-course-card__restore:disabled { opacity: .55; cursor: wait; }
.archive-course-card__restore:focus-visible { outline: 3px solid #9db4d8; outline-offset: 2px; }

.bank-workspace { padding: 1.5rem; }
.bank-heading { display: flex; align-items: center; justify-content: space-between; gap: 2rem; padding: 1.7rem 2rem; margin-bottom: 1.25rem; border-radius: 18px; background: #1d3461; box-shadow: 0 14px 30px rgba(24, 48, 88, .14); }
.bank-heading h2 { margin: .2rem 0 .4rem; color: #fff; font: 750 1.7rem 'Poppins', sans-serif; }
.bank-heading p { max-width: 580px; margin: 0; color: #c8d6eb; font-size: .84rem; line-height: 1.6; }
.bank-eyebrow { color: #7488a6; font-size: .67rem; font-weight: 800; letter-spacing: .11em; }
.bank-heading .bank-eyebrow { color: #9db8de; }
.bank-heading__stats { display: flex; align-items: center; gap: 1.5rem; flex: none; }
.bank-heading__stats span { display: grid; gap: .05rem; color: #bdcde5; font-size: .72rem; }
.bank-heading__stats strong { color: #fff; font: 750 1.45rem 'Poppins', sans-serif; }
.bank-layout { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(340px, .85fr); gap: 1.2rem; align-items: start; }
.bank-list-panel, .bank-editor-card { min-width: 0; padding: 1.35rem; border: 1px solid #dfe7f1; border-radius: 16px; background: #fff; box-shadow: 0 10px 28px rgba(25, 50, 88, .055); }
.bank-panel-heading { display: flex; align-items: center; gap: .85rem; margin-bottom: 1rem; }
.bank-panel-heading h2, .bank-panel-heading h3 { margin: .1rem 0 0; color: #1d3461; font: 750 1.08rem 'Poppins', sans-serif; }
.bank-panel-heading__icon { display: inline-flex; align-items: center; justify-content: center; width: 42px; height: 42px; flex: none; border-radius: 11px; background: #eaf0f8; color: #244a80; }
.bank-panel-heading__icon svg { width: 19px; height: 19px; }
.bank-filter-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(145px, .45fr); gap: .65rem; margin: 1rem 0 .55rem; }
.bank-filter-row .create-panel__input { min-height: 43px; }
.bank-help { margin: .5rem 0 1rem; color: #667991; font-size: .76rem; line-height: 1.55; }
.bank-item-list { display: grid; align-content: start; gap: .7rem; max-height: 700px; overflow: auto; padding-right: .2rem; }
.bank-batch { border: 1px solid #dce5ef; border-radius: 12px; background: #fff; overflow: hidden; }
.bank-batch > summary { display: flex; align-items: center; gap: .7rem; padding: .92rem 1rem; color: #254264; background: #f9fbfd; cursor: pointer; list-style: none; }
.bank-batch > summary::-webkit-details-marker { display: none; }
.bank-batch > summary::after { content: '⌄'; color: #647b9b; font-size: 1.2rem; line-height: 1; transition: transform .2s; }
.bank-batch[open] > summary::after { transform: rotate(180deg); }
.bank-batch > summary strong { flex: 1; min-width: 0; font: 700 .83rem 'Poppins', sans-serif; overflow-wrap: anywhere; }
.bank-batch > summary span:not(.bank-batch__index) { color: #687c96; font-size: .72rem; white-space: nowrap; }
.bank-batch[open] > summary { background: #f2f5f9; border-bottom: 1px solid #e3eaf2; }
.bank-batch__index { display: inline-grid; place-items: center; width: 28px; height: 28px; flex: none; border-radius: 8px; background: #e6edf7; color: #355982; font-size: .7rem; font-weight: 800; }
.bank-batch .bank-item, .bank-batch .bank-select-item { margin: .45rem .65rem; }
.bank-batch__actions { display: flex; justify-content: flex-end; padding: .65rem .8rem 0; }
.bank-item { display: flex; align-items: flex-start; justify-content: space-between; gap: .8rem; padding: .85rem; border: 1px solid #e6ebf2; border-radius: 10px; background: #fff; }
.bank-item__main { min-width: 0; overflow-wrap: anywhere; }
.bank-item__main p { margin: .32rem 0 .45rem; color: #203858; font-size: .84rem; font-weight: 650; line-height: 1.5; white-space: pre-wrap; }
.bank-item__type { color: #59779c; font-size: .66rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.bank-item__details { color: #506882; font-size: .76rem; white-space: pre-line; }
.bank-item__details summary { width: fit-content; color: #315d91; font-weight: 700; cursor: pointer; }
.bank-item__details[open] { margin-top: .55rem; padding: .65rem .8rem; border-radius: 8px; background: #f2f5f9; }
.bank-item__details ul { margin: .5rem 0; padding-left: 1.3rem; }
.bank-item__delete { flex: none; border: 0; background: none; color: #a83d4a; font: 700 .74rem 'Poppins', sans-serif; cursor: pointer; }
.bank-item__delete:hover:not(:disabled) { text-decoration: underline; }
.bank-item__delete:disabled { opacity: .5; cursor: default; }
.bank-editor { display: grid; gap: .75rem; }
.bank-editor-switch { display: grid; grid-template-columns: 1fr 1fr; gap: .25rem; padding: .3rem; border-radius: 12px; background: #eaf0f7; }
.bank-editor-switch button { padding: .72rem .5rem; border: 0; border-radius: 9px; background: transparent; color: #5a6e88; font: 700 .78rem 'Poppins', sans-serif; cursor: pointer; }
.bank-editor-switch button.active { background: #fff; color: #1d3461; box-shadow: 0 2px 8px rgba(24, 48, 88, .11); }
.bank-editor-switch button:focus-visible, .bank-batch > summary:focus-visible, .bank-type-pills label:focus-within, .bank-select-item:focus-within { outline: 3px solid #94b8e9; outline-offset: 2px; }
.bank-editor-card > p { margin: 0 0 .5rem; color: #647991; font-size: .8rem; line-height: 1.55; }
.bank-form, .bank-form label { display: grid; gap: .45rem; }
.bank-form { gap: 1rem; margin-top: 1.1rem; }
.bank-form label, .bank-type-fieldset legend { color: #314b6d; font-size: .76rem; font-weight: 750; }
.bank-form small { color: #75869c; font-weight: 500; }
.bank-form .primary-btn { justify-self: stretch; padding: .78rem 1rem; }
.bank-textarea { min-height: 100px; resize: vertical; }
.bank-type-fieldset, .bank-choice-fieldset { margin: 0; padding: 0; border: 0; }
.bank-type-fieldset legend, .bank-choice-fieldset legend { margin-bottom: .5rem; }
.bank-type-pills { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; }
.bank-type-pills label { display: flex; align-items: center; min-height: 43px; padding: .6rem .75rem; border: 1px solid #dde5ef; border-radius: 9px; background: #f7f9fc; color: #4e627e; font-size: .75rem; cursor: pointer; }
.bank-type-pills label.active { border-color: #1d3461; background: #1d3461; color: #fff; }
.bank-type-pills input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.bank-choice-fieldset { padding: .9rem; border: 1px solid #e1e7f0; border-radius: 10px; background: #f8fafc; }
.bank-choice-fieldset legend { color: #516789; font-size: .75rem; font-weight: 700; }
.bank-choice-row { display: flex; align-items: center; gap: .5rem; margin: .4rem 0; }
.bank-choice-row .create-panel__input { flex: 1; min-width: 0; }
.bank-checkbox { display: flex !important; align-items: center; gap: .5rem; }
.bank-remove-choice, .bank-text-button { border: 0; background: none; color: #315684; font-weight: 700; cursor: pointer; }
.bank-select-panel { min-width: 0; }
.draft-bank-card { padding: 1.35rem; }
.draft-bank-card > p { margin-bottom: .6rem; }
.draft-bank-summary { display: flex; align-items: center; justify-content: space-between; gap: .5rem; padding: .7rem .8rem; border-radius: 9px; background: #f1f5fa; color: #5f7490; font-size: .7rem; }
.draft-bank-summary span { display: flex; align-items: baseline; gap: .25rem; }
.draft-bank-summary strong { color: #1d3461; font-size: .9rem; }
.draft-bank-empty { padding: 1.3rem; border-radius: 10px; background: #f5f7fb; color: #223d60; }
.draft-bank-empty p { color: #637992; font-size: .79rem; line-height: 1.5; }
.bank-select-list { display: grid; align-content: start; gap: .6rem; max-height: 525px; overflow: auto; padding-right: .2rem; }
.bank-select-item { display: flex; align-items: flex-start; gap: .7rem; padding: .78rem; border: 1px solid #e3eaf2; border-radius: 9px; background: #fff; cursor: pointer; }
.bank-select-item:hover { background: #f7f9fc; }
.bank-select-item--added { opacity: .62; cursor: default; }
.bank-select-item input { margin-top: .15rem; accent-color: #1d3461; }
.bank-select-item span { display: grid; gap: .2rem; min-width: 0; overflow-wrap: anywhere; }
.bank-select-item small { color: #7185a1; font-size: .67rem; font-weight: 700; }
.bank-select-item strong { color: #263c5b; font-size: .79rem; font-weight: 600; line-height: 1.45; white-space: pre-wrap; }
.bank-select-item em { margin-left: auto; color: #52775e; font-size: .68rem; font-style: normal; font-weight: 700; }
.bank-select-actions { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .6rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5ebf2; }
.bank-select-actions > span { color: #6a7e97; font-size: .72rem; }
.draft-bank-link { margin-top: .85rem; padding: .2rem 0; font-size: .76rem; }
.bank-exam-preview { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: start; gap: .6rem; }
.bank-exam-preview p { white-space: pre-wrap; overflow-wrap: anywhere; }
.bank-exam-preview__body { min-width: 0; }
@media (max-width: 1050px) { .bank-layout { grid-template-columns: 1fr; } }
@media (max-width: 700px) { .bank-heading { flex-direction: column; align-items: flex-start; padding: 1.3rem; } .bank-filter-row { grid-template-columns: 1fr; } .bank-workspace { padding: 1rem; } .bank-heading__stats { gap: 2rem; } }

@media (max-width: 720px) {
  .archive-heading { align-items: flex-start; flex-direction: column; }
  .stats-backdrop { padding: 0; align-items: stretch; }
  .stats-shell { max-height: 100vh; border-radius: 0; border: none; }
  .stats-header { padding: 1.1rem 1rem; }
  .stats-title { font-size: 1.4rem; }
  .stats-summary-bar { grid-template-columns: repeat(3, minmax(0, 1fr)); padding: 1rem; gap: 0.5rem; }
  .stats-summary-pill { padding: 0.8rem; }
  .ssp-num { font-size: 1.65rem; }
  .ssp-lbl { font-size: 0.72rem; }
  .stats-body { padding: 0 1rem 1rem; }
  .stats-examinees-section { padding: 1rem; }
  .stats-refresh-note { display: none; }
}
@media (max-width: 480px) {
  .stats-summary-bar { grid-template-columns: 1fr; }
  .stats-summary-pill { flex-direction: row; align-items: baseline; justify-content: space-between; }
}
</style>

