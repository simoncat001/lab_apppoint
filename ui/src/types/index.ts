// ==================== User Types ====================
export interface User {
    id: number
    username: string
    email: string
    first_name: string
    last_name: string
    is_active: boolean
    is_verified: boolean
    status?: 'INACTIVE' | 'ACTIVE' | 'VERIFIED'
    is_staff: boolean
    is_superuser: boolean
    badge_number?: number
    phone?: string
    phone_number?: string
    auth_source?: 'local' | 'security_server'
    priority_reservation?: boolean
    special_course_access?: boolean
    managed_tool_ids?: number[]
    date_joined: string
    last_login?: string
}

// ==================== Auth Types ====================
export interface LoginRequest {
    username?: string
    password?: string
    auth_source?: 'auto' | 'internal' | 'external'
    target?: string
    type?: 'email' | 'phone'
    code?: string
}

export interface LoginResponse {
    access_token: string
    token_type: string
    user: User
}

// ==================== Tool Types ====================
export interface Tool {
    id: number
    name: string
    visible: boolean
    operational: boolean
    location?: string
    phone_number?: string
    description?: string
    serial?: string
    category_id?: number
    project_id?: number | null
    category?: ToolCategory
    project?: Project
    tags?: ToolTag[]
    tag_ids?: number[]
    requires_reservation?: boolean
    price_type?: number
    price_per_use?: number
    price_per_hour?: number
    maximum_reservations_per_day?: number | null
    image?: string
    images?: ToolImage[]
    restrict_external_access?: boolean
    created_at?: string
}

export interface ToolImage {
    id: number
    tool_id: number
    path: string
    sort_order: number
    created_at?: string
}

export interface ToolUserAccess {
    id: number
    tool_id: number
    user_id: number
    username: string
    first_name: string
    last_name: string
    granted_by?: number
    granted_at?: string
}

export interface ToolCategory {
    id: number
    name: string
}

export interface ToolTag {
    id: number
    name: string
}

export interface ToolAdmin {
    id: number
    username: string
    first_name?: string
    last_name?: string
}

export interface ToolProjectSuggestRequest {
    name: string
    location?: string
    description?: string
}

export interface ToolProjectSuggestCandidate {
    project_id: number
    project_name: string
    score: number
    reason: string
}

export interface ToolProjectSuggestResponse {
    matched: boolean
    project_id?: number
    project_name?: string
    score: number
    reason: string
    candidates: ToolProjectSuggestCandidate[]
}

export interface ToolEnableRequest {
    user_id: number
    project_id: number
    operator_id?: number
    note?: string
}

export interface ToolDisableRequest {
    note?: string
    run_data?: string
}

// ==================== Project Types ====================
export interface Project {
    id: number
    name: string
    external_display_name?: string | null
    account_id?: number | null
    application_identifier?: string
    start_date?: string
    end_date?: string
    active: boolean
    allow_external_booking_request?: boolean
}

export type ProjectJoinRequestStatus =
    | 'PENDING'
    | 'APPROVED'
    | 'REJECTED'
    | 'CANCELLED'

export interface ProjectJoinRequest {
    id: number
    requester_user_id: number
    source_project_id?: number | null
    target_project_id: number
    status: ProjectJoinRequestStatus
    reason?: string | null
    review_comment?: string | null
    reviewer_user_id?: number | null
    created_at: string
    updated_at: string
    reviewed_at?: string | null
    requester?: User
    reviewer?: User
    source_project?: Project | null
    target_project?: Project | null
}

// ==================== Reservation Types ====================
export interface Reservation {
    id: number
    user_id: number
    tool_id?: number
    area_id?: number
    project_id: number
    payer_account_id?: number | null
    start: string
    end: string
    cancelled: boolean
    missed: boolean
    additional_information?: string
    self_configuration: boolean
    payment_status?: string
    payment_amount?: number
    payment_method?: string
    paid_at?: string
    actual_start?: string
    actual_end?: string
    completion_note?: string
    completed_by_id?: number
    completed_at?: string
    created_at?: string
    // 关联对象
    user?: User
    tool?: Tool
    project?: Project
    area?: Area
}

export interface ReservationOccupiedSlot {
    id: number
    start: string
    end: string
}

// ==================== Collaboration Record Types ====================
export type CollaborationRecordType =
    | 'tool_note'
    | 'reservation_note'
    | 'experiment_note'
    | 'maintenance_experience'
    | 'sop'
    | 'faq'
    | 'case_study'
    | 'issue'

export type CollaborationVisibility =
    | 'project'
    | 'staff'
    | 'tool_managers'
    | 'author_private'

export type CollaborationStatus = 'draft' | 'published' | 'archived'

export interface CollaborationRecord {
    id: number
    project_id: number
    tool_id?: number | null
    reservation_id?: number | null
    usage_event_id?: number | null
    task_id?: number | null
    maintenance_record_id?: number | null
    author_id: number
    author_username?: string | null
    author_display_name?: string | null
    record_type: CollaborationRecordType
    title: string
    content: string
    content_format: string
    visibility: CollaborationVisibility
    status: CollaborationStatus
    pinned: boolean
    created_at: string
    updated_at: string
}

export interface CollaborationRecordQuery {
    tool_id?: number
    reservation_id?: number
    record_type?: CollaborationRecordType
    status?: CollaborationStatus
    visibility?: CollaborationVisibility
    keyword?: string
    mine?: boolean
    page?: number
    page_size?: number
}

export interface CollaborationRecordPayload {
    tool_id?: number
    reservation_id?: number
    record_type: CollaborationRecordType
    title: string
    content: string
    content_format?: string
    visibility?: CollaborationVisibility
    status?: CollaborationStatus
}

export interface Area {
    id: number
    name: string
    category?: string
}

// ==================== Announcement Types ====================
export interface Announcement {
    id: number
    title: string
    content: string
    published: boolean
    created_at: string
    updated_at: string
    author_id?: number
    project_id?: number
    author_username?: string
    author_display_name?: string
}

// ==================== Training Types ====================
export interface TrainingCategory {
    id: number
    name: string
}

export interface TrainingCourse {
    id: number
    title: string
    summary?: string
    cover_url?: string
    category_id?: number
    project_id?: number
    sort_order: number
    published: boolean
    created_at: string
    updated_at: string
}

export interface TrainingChapter {
    id: number
    course_id: number
    title: string
    summary?: string
    sort_order: number
    published: boolean
    created_at: string
    updated_at: string
}

export interface TrainingContent {
    id: number
    title: string
    description?: string
    file_url?: string
    category_id?: number
    chapter_id?: number
    project_id?: number
    content_type: 'link' | 'document' | 'video'
    sort_order: number
    estimated_minutes: number
    published: boolean
    created_at: string
    updated_at: string
}

export interface TrainingRecord {
    id: number
    user_id: number
    content_id: number
    completed_at: string
}

export interface TrainingContentProgress extends TrainingContent {
    learned: boolean
    learned_at?: string | null
}

export interface TrainingChapterDetail extends TrainingChapter {
    materials: TrainingContentProgress[]
    total_materials: number
    completed_materials: number
    progress_percent: number
}

export interface TrainingCourseDetail extends TrainingCourse {
    chapters: TrainingChapterDetail[]
    total_materials: number
    completed_materials: number
    progress_percent: number
}

export interface TrainingOverview {
    courses: TrainingCourseDetail[]
    standalone_contents: TrainingContentProgress[]
    total_materials: number
    completed_materials: number
    progress_percent: number
}

export type ExamQuestionType = 'single' | 'multi' | 'truefalse' | 'fill' | 'essay'

export interface ExamQuestion {
    id: number
    question: string
    type: ExamQuestionType
    options?: string[]
    score: number
}

export interface ExamPaper {
    id: number
    project_id?: number
    name: string
    description?: string
    compose_type: 'manual' | 'random'
    total_score: number
    pass_score: number
    duration_minutes: number
    show_result_immediately: boolean
    published: boolean
    created_by?: number
    created_at: string
    updated_at: string
    question_count: number
}

export interface ExamStartResponse {
    attempt_id: number
    paper_id: number
    paper_name: string
    total_score: number
    questions: ExamQuestion[]
    pass_score: number
    duration_minutes: number
    remaining_minutes?: number
    started_at: string
}

export interface ExamAttemptSummary {
    id: number
    user_id: number
    paper_id?: number
    started_at: string
    completed_at?: string | null
    score: number
    total_score: number
    passed: boolean
    manual_graded: boolean
}

// ==================== Maintenance Types ====================
export interface MaintenanceRecord {
    id: number
    tool_id: number
    staff_id?: number
    performed_at?: string
    next_due_at?: string
    description: string
}

// ==================== Reports Types ====================
export interface UserReport {
    total: number
    active: number
    new_count: number
    login_count?: number
    export_count?: number
}

export interface ReservationReport {
    total: number
    cancelled: number
    paid: number
}

export interface ToolReport {
    total: number
    usage_by_tool: Record<string, number>
}

export interface ProjectReportTopTool {
    tool_id: number
    tool_name: string
    reservation_count: number
}

export interface ProjectReportItem {
    project_id: number
    project_name: string
    external_display_name?: string | null
    active: boolean
    tool_count: number
    active_tool_count: number
    idle_tool_count: number
    reservation_count: number
    cancelled_reservation_count: number
    paid_usage_count: number
    top_tools: ProjectReportTopTool[]
}

export interface ProjectReportGlobalTool extends ProjectReportTopTool {
    project_id?: number | null
    project_name?: string | null
}

export interface ProjectReportSummary {
    total_projects: number
    active_projects: number
    inactive_projects: number
    uncategorized_tools: number
    project_reports: ProjectReportItem[]
    top_tools: ProjectReportGlobalTool[]
}

// ==================== Account Types ====================
export interface Account {
    id: number
    name: string
    user_id?: number | null
    active: boolean
    type_id?: number | null
    start_date?: string
    note?: string
    balance?: number
    credit_limit?: number
    credit_score?: number
    member_ids?: number[]
    members?: User[]
    type?: AccountType
    default_project_id?: number | null
    default_project_name?: string | null
    project_binding_locked?: boolean
}

export interface AccountType {
    id: number
    name: string
    display_order?: number
}

export type AccountMembershipChangeRequestStatus =
    | 'PENDING'
    | 'APPROVED'
    | 'REJECTED'
    | 'CANCELLED'

export interface AccountMembershipChangeRequest {
    id: number
    requester_user_id: number
    source_account_id?: number | null
    target_account_id?: number | null
    status: AccountMembershipChangeRequestStatus
    reason?: string | null
    review_comment?: string | null
    reviewer_user_id?: number | null
    created_at: string
    updated_at: string
    reviewed_at?: string | null
    requester?: User
    reviewer?: User
    source_account?: Account | null
    target_account?: Account | null
}

// ==================== UsageEvent Types ====================
export interface UsageEvent {
    id: number
    tool_id: number
    user_id: number
    operator_id: number
    project_id: number
    start: string
    end?: string
    validated: boolean
    validated_by_id?: number
    waived: boolean
    waived_by_id?: number
    waived_on?: string
    note?: string
    amount?: number
    duration_minutes?: number
    actual_duration_minutes?: number
    // 关联对象
    user?: User
    tool?: Tool
    project?: Project
}

export interface UsageEventStats {
    total_count: number
    total_duration_minutes: number
    average_duration_minutes: number
    validated_count: number
    pending_count: number
    charged_count: number
    charged_total_amount: number
    by_tool: Record<number, number>
    by_user: Record<number, number>
}

// ==================== Task Types ====================
export interface Task {
    id: number
    tool_id?: number
    urgency: TaskUrgency | string | number
    creation_time: string
    creator_id: number
    last_updated: string
    last_updated_by_id?: number
    resolved: boolean
    cancelled?: boolean
    resolution_time?: string
    resolver_id?: number
    category_id?: number
    problem_category_id?: number
    problem_description: string
    progress_description?: string
    resolution_description?: string
    status?: string
    created_at?: string
    // 关联对象
    tool?: Tool
    creator?: User
}

export enum TaskUrgency {
    LOW = 'low',
    NORMAL = 'normal',
    HIGH = 'high',
    CRITICAL = 'critical',
}

export interface TaskCategory {
    id: number
    name: string
    stage: TaskCategoryStage
}

export enum TaskCategoryStage {
    INITIAL_ASSESSMENT = 'initial_assessment',
    COMPLETION = 'completion',
    MAINTENANCE = 'maintenance',
}

// ==================== StaffCharge Types ====================
export interface StaffCharge {
    id: number
    staff_member_id: number
    customer_id: number
    project_id: number
    start: string
    end?: string
    validated: boolean
    validated_by_id?: number
    waived: boolean
    waived_by_id?: number
    waived_on?: string
    note?: string
}

// ==================== Configuration Types ====================
export interface Configuration {
    id: number
    name: string
    tool_id: number
    configurable_item_name?: string
    advance_notice_limit: number
    display_order: number
    prompt?: string
    current_settings?: string
    current_setting?: string
    current_setting_color?: string
    available_settings?: string
    calendar_colors?: string
    absence_string?: string
    qualified_users_are_maintainers: boolean
    exclude_from_configuration_agenda: boolean
    enabled: boolean
    // 关联对象
    configuration_options?: ConfigurationOption[]
}

export interface ConfigurationOption {
    id: number
    name: string
    configuration_id?: number
    reservation_id: number
    current_setting?: string
    available_settings?: string
    calendar_colors?: string
    absence_string?: string
}

export interface ConfigurationHistory {
    id: number
    configuration_id: number
    user_id: number
    modification_time: string
    item_name?: string
    slot: number
    setting: string
}

// ==================== Common Types ====================
export interface PaginationParams {
    skip?: number
    limit?: number
}

export interface ApiResponse<T> {
    data: T
    message?: string
    status: number
}

export interface TableColumn {
    prop: string
    label: string
    width?: string | number
    minWidth?: string | number
    fixed?: boolean | 'left' | 'right'
    sortable?: boolean
}

// ==================== Billing Types ====================
export interface Bill {
    id: number
    account_id: number
    account_name?: string
    user_id?: number
    username?: string
    reference_number: string
    period_start: string
    period_end: string
    issued_date: string
    due_date?: string
    total_amount: number
    status: string
    
    // Optional relations if needed
    account?: Account
}

export interface BillUserBasic {
    id: number
    username: string
    email: string
    first_name: string
    last_name: string
}

export interface BillUsageEventUser {
    id: number
    username: string
}

export interface BillUsageEventTool {
    id: number
    name: string
}

export interface BillUsageEventProject {
    id: number
    name: string
}

export interface BillUsageEvent {
    id: number
    tool_id: number
    user_id: number
    operator_id: number
    project_id: number
    start: string
    end?: string
    has_ended: number
    validated: boolean
    validated_by_id?: number
    waived: boolean
    waived_on?: string
    waived_by_id?: number
    note?: string
    amount?: number

    user?: BillUsageEventUser
    tool?: BillUsageEventTool
    project?: BillUsageEventProject
}

export interface BillDetail extends Bill {
    user?: BillUserBasic
    usage_events: BillUsageEvent[]
}

export interface BillGenerationRequest {
    account_ids?: number[]
}

export interface BillUpdateRequest {
    status?: string
    due_date?: string | null
}
