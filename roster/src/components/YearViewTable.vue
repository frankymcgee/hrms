<template>
  <div
    class="year-roster-shell flex flex-col gap-4"
    :class="[
      loading && 'animate-pulse pointer-events-none',
      showShiftAssignmentDialog && 'year-dialog-open',
    ]"
    :style="maxHeightPx ? { height: maxHeightPx + 'px' } : {}"
  >
    <!-- Annual project / planning view. This is intentionally separate from employees. -->
    <section v-if="projectRows.length" class="year-roster-panel rounded-lg border bg-white">
      <div
        ref="projectScroller"
        class="year-roster-scroller overflow-auto"
        :style="{ maxHeight: projectTableMaxHeight + 'px' }"
        @scroll="onProjectScroll"
      >
        <div class="year-table-stage">
          <div
            v-if="showTodayOverlay"
            class="year-today-overlay"
            :style="todayOverlayStyle"
            aria-hidden="true"
          />

          <table class="year-roster-table border-separate border-spacing-0">
            <colgroup>
              <col class="year-left-colgroup" />
              <col v-for="day in daysOfYear" :key="`project-col-${day.date}`" class="year-day-colgroup" />
            </colgroup>
          <thead>
            <tr>
              <th rowspan="2" class="year-left-header year-left-col year-project-legend-header border-b border-r bg-white text-left">
                <div class="year-project-header-content px-2 py-1.5">
                  <div class="flex items-center gap-1.5 text-xs font-semibold text-gray-800">
                    <span class="year-project-header-icon">▱</span>
                    <span>Projects</span>
                  </div>

                  <div class="mt-1 text-[10px] font-semibold leading-none text-gray-600">Legend</div>

                  <div class="year-project-legend mt-1">
                    <div class="year-project-legend-item">
                      <span class="year-legend-icon year-legend-po-entered">✓</span>
                      <span>PO Entered</span>
                    </div>
                    <div class="year-project-legend-item">
                      <span class="year-legend-icon year-legend-po-missing">×</span>
                      <span>PO Missing</span>
                    </div>
                    <div class="year-project-legend-item">
                      <span class="year-legend-icon year-legend-ds-requested">☼</span>
                      <span># DS Requested</span>
                    </div>
                    <div class="year-project-legend-item">
                      <span class="year-legend-icon year-legend-ns-requested">◔</span>
                      <span># NS Requested</span>
                    </div>
                  </div>
                </div>
              </th>

              <th
                v-for="month in monthGroups"
                :key="`project-month-${month.key}`"
                class="year-month-header border-b border-r bg-gray-50 text-center font-semibold text-gray-700"
                :colspan="month.days"
              >
                {{ month.label }}
              </th>
            </tr>
            <tr>
              <th
                v-for="day in daysOfYear"
                :key="`project-day-${day.date}`"
                class="year-day-header border-b border-r bg-white text-center font-medium"
                :class="{
                  'year-month-start': day.isMonthStart,
                  'year-weekend': day.isWeekend,
                }"
                :title="dayjs(day.date).format('dddd, DD MMMM YYYY')"
              >
                <div class="text-[10px] leading-none text-gray-500">{{ day.weekday }}</div>
                <div class="mt-0.5 text-[11px] leading-none">{{ day.day }}</div>
              </th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="project in projectRows" :key="project.project_name" class="year-project-row">
              <td class="year-left-col border-b border-r bg-white">
                <div class="truncate px-2 text-xs font-medium text-gray-700" :title="project.project_name">
                  {{ project.project_name }}
                </div>
              </td>

              <td
                v-for="segment in projectSegments(project)"
                :key="segment.key"
                class="year-cell year-project-cell border-b border-r text-center"
                :class="projectSegmentClass(segment)"
                :style="projectSegmentStyle(segment)"
                :title="segment.title"
                :colspan="segment.days"
              >
                <div v-if="segment.active" class="year-project-span-content">
                  <span
                    class="year-project-status-icon"
                    :class="segment.poEntered ? 'year-project-po-entered' : 'year-project-po-missing'"
                    :title="segment.poEntered ? 'PO Entered' : 'PO Missing'"
                  >
                    {{ segment.poEntered ? '✓' : '×' }}
                  </span>

                  <span class="year-project-span-name truncate">
                    {{ segment.label }}
                  </span>

                  <span class="year-project-span-date">
                    {{ segment.subline }}
                  </span>

                  <span class="year-project-request year-project-request-ds" title="# DS Requested">☼</span>
                  <span class="year-project-request-count">{{ segment.dsRequested || 0 }}</span>

                  <span class="year-project-request year-project-request-ns" title="# NS Requested">◔</span>
                  <span class="year-project-request-count">{{ segment.nsRequested || 0 }}</span>
                </div>
              </td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Annual employee roster view. This scrolls separately from the project table. -->
    <section class="year-roster-panel year-employee-panel flex min-h-0 flex-1 flex-col rounded-lg border bg-white">
      <div
        ref="employeeScroller"
        class="year-roster-scroller min-h-0 flex-1 overflow-auto"
        :style="{ maxHeight: employeeTableMaxHeight + 'px' }"
        @scroll="onEmployeeScroll"
      >
        <div class="year-table-stage">
          <div
            v-if="showTodayOverlay"
            class="year-today-overlay"
            :style="todayOverlayStyle"
            aria-hidden="true"
          />

          <table class="year-roster-table border-separate border-spacing-0">
            <colgroup>
              <col class="year-left-colgroup" />
              <col v-for="day in daysOfYear" :key="`employee-col-${day.date}`" class="year-day-colgroup" />
            </colgroup>
          <thead>
            <tr>
              <th rowspan="2" class="year-left-header year-left-col year-employee-search-header border-b border-r bg-white text-left">
                <div class="year-employee-header-content px-2 py-1.5">
                  <div class="flex items-center gap-2">
                    <div class="text-xs font-semibold text-gray-700">Employee</div>
                  </div>

                  <div class="year-employee-search">
                    <Autocomplete
                      :options="employeeSearchOptions"
                      v-model="employeeSearch"
                      placeholder="Search Employee"
                      :multiple="true"
                    />
                  </div>

                  <div class="year-employee-legend-title">Legend</div>

                  <div class="year-employee-legend">
                    <div class="year-employee-legend-item">
                      <span class="year-employee-legend-dot year-employee-legend-fifo"></span>
                      <span>Fly-in/Fly-out</span>
                    </div>
                    <div class="year-employee-legend-item">
                      <span class="year-employee-legend-dot year-employee-legend-ds"></span>
                      <span>DS</span>
                    </div>
                    <div class="year-employee-legend-item">
                      <span class="year-employee-legend-dot year-employee-legend-ns"></span>
                      <span>NS</span>
                    </div>
                    <div class="year-employee-legend-item">
                      <span class="year-employee-legend-dot year-employee-legend-pth"></span>
                      <span>PTH</span>
                    </div>
                  </div>
                </div>
              </th>

              <th
                v-for="month in monthGroups"
                :key="`employee-month-${month.key}`"
                class="year-month-header border-b border-r bg-gray-50 text-center font-semibold text-gray-700"
                :colspan="month.days"
              >
                {{ month.label }}
              </th>
            </tr>
            <tr>
              <th
                v-for="day in daysOfYear"
                :key="`employee-day-${day.date}`"
                class="year-day-header border-b border-r bg-white text-center font-medium"
                :class="{
                  'year-month-start': day.isMonthStart,
                  'year-weekend': day.isWeekend,
                }"
                :title="dayjs(day.date).format('dddd, DD MMMM YYYY')"
              >
                <div class="text-[10px] leading-none text-gray-500">{{ day.weekday }}</div>
                <div class="mt-0.5 text-[11px] leading-none">{{ day.day }}</div>
              </th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="employee in visibleEmployees" :key="employee.name" class="year-employee-row">
              <td class="year-left-col border-b border-r bg-white">
                <div class="px-2 leading-tight">
                  <div class="truncate text-xs font-semibold text-gray-800" :title="employeeTitle(employee)">
                    {{ employeeDisplayName(employee) }}
                  </div>
                  <div class="truncate text-[10px] text-gray-500" :title="employeeSubline(employee)">
                    {{ employeeSubline(employee) }}
                  </div>
                </div>
              </td>

              <td
                v-for="day in daysOfYear"
                :key="`${employee.name}-${day.date}`"
                class="year-cell cursor-pointer border-b border-r text-center"
                :class="{
                  'year-month-start': day.isMonthStart,
                  'year-weekend': day.isWeekend,
                }"
                :style="employeeCellStyle(employee.name, day.date)"
                :title="employeeCellTitle(employee.name, day.date)"
                @click="openEmployeeCell(employee.name, day.date)"
              >
                {{ employeeCellLabel(employee.name, day.date) }}
              </td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>

  <ShiftAssignmentDialog
    v-model="showShiftAssignmentDialog"
    :isDialogOpen="showShiftAssignmentDialog"
    :shiftAssignmentName="shiftAssignment"
    :selectedCell="selectedCell"
    :employees="employees"
    @fetchEvents="
      events.fetch();
      showShiftAssignmentDialog = false;
    "
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import colors from 'tailwindcss/colors'
import { Autocomplete, createResource } from 'frappe-ui'
import type { Dayjs } from 'dayjs'

import { dayjs, raiseToast } from '../utils'
import type { EmployeeFilters, ShiftFilters } from '../views/MonthView.vue'
import ShiftAssignmentDialog from './ShiftAssignmentDialog.vue'

type Color =
  | 'blue'
  | 'cyan'
  | 'fuchsia'
  | 'green'
  | 'lime'
  | 'orange'
  | 'pink'
  | 'red'
  | 'violet'
  | 'yellow'
  | 'gray'

type Employee = {
  name: string
  employee_name: string
  first_name?: string
  last_name?: string
  designation?: string
  department?: string
  image?: string
}

interface HolidayWithDate {
  holiday: string
  holiday_date: string
  description: string
  weekly_off: 0 | 1
}

interface LeaveApplication {
  leave: string
  leave_type: string
  from_date: string
  to_date: string
}

type ShiftAssignment = {
  name: string
  shift_type: string
  shift_location?: string
  status: string
  start_date: string
  end_date?: string | null
  start_time?: string
  end_time?: string
  color?: string
  custom_project?: string
  custom_project_name?: string
  customer_abbreviation?: string | null
  note?: string | null
}

type RawEvent = HolidayWithDate | LeaveApplication | ShiftAssignment
type Events = Record<string, RawEvent[]>

type YearCell =
  | { type: 'holiday'; label: string; title: string }
  | { type: 'leave'; label: string; title: string }
  | { type: 'shift'; label: string; title: string; shift: ShiftAssignment; shifts: ShiftAssignment[] }

type MappedEvents = Record<string, Record<string, YearCell>>

type ProjectDayCell = {
  label: string
  count: number
  color?: string
  shift_types?: string[]
  employees?: string[]
}

type ProjectRow = {
  project: string
  project_name: string
  status?: string
  po_entered?: boolean
  ds_requested?: number
  ns_requested?: number
  customer_color?: string | null
  assignments: Record<string, ProjectDayCell>
}

type YearEventsResponse = {
  events?: Events
  project_rows?: ProjectRow[]
}

const emit = defineEmits<{ (e: 'hscroll', left: number): void }>()
const employeeScroller = ref<HTMLDivElement | null>(null)
const projectScroller = ref<HTMLDivElement | null>(null)

const props = defineProps<{
  firstOfMonth: Dayjs
  employees: Employee[]
  employeeFilters: { [K in keyof EmployeeFilters]?: string }
  shiftFilters: { [K in keyof ShiftFilters]?: string }
  maxHeightPx?: number
}>()

const loading = ref(true)
const employeeSearch = ref<{ value: string; label: string }[]>()
const shiftAssignment = ref<string>('')
const showShiftAssignmentDialog = ref(false)
const selectedCell = ref<{ employee: string; date: string }>({ employee: '', date: '' })

const LEFT_COLUMN_WIDTH = 300
const DAY_COLUMN_WIDTH = 28

let syncingHorizontalScroll = false

function syncHorizontalScroll(source: 'project' | 'employee') {
  const sourceScroller = source === 'project' ? projectScroller.value : employeeScroller.value
  const targetScroller = source === 'project' ? employeeScroller.value : projectScroller.value

  if (!sourceScroller) return

  const left = sourceScroller.scrollLeft

  if (syncingHorizontalScroll) {
    emit('hscroll', left)
    return
  }

  if (targetScroller && Math.abs(targetScroller.scrollLeft - left) > 1) {
    syncingHorizontalScroll = true
    targetScroller.scrollLeft = left

    window.requestAnimationFrame(() => {
      syncingHorizontalScroll = false
    })
  }

  emit('hscroll', left)
}

function onProjectScroll() {
  syncHorizontalScroll('project')
}

function onEmployeeScroll() {
  syncHorizontalScroll('employee')
}

const firstOfYear = computed(() => props.firstOfMonth.startOf('year'))

const daysOfYear = computed(() => {
  const days = []
  let date = firstOfYear.value.startOf('day')
  const end = firstOfYear.value.endOf('year')

  while (date.isSameOrBefore(end, 'day')) {
    days.push({
      date: date.format('YYYY-MM-DD'),
      day: date.format('D'),
      weekday: date.format('dd').charAt(0),
      month: date.format('MMM'),
      monthKey: date.format('YYYY-MM'),
      isMonthStart: date.date() === 1,
      isWeekend: [0, 6].includes(date.day()),
      isToday: date.isSame(dayjs(), 'day'),
    })
    date = date.add(1, 'day')
  }

  return days
})

const monthGroups = computed(() => {
  const groups: { key: string; label: string; days: number }[] = []
  for (const day of daysOfYear.value) {
    const last = groups[groups.length - 1]
    if (!last || last.key !== day.monthKey) {
      groups.push({ key: day.monthKey, label: day.month, days: 1 })
    } else {
      last.days += 1
    }
  }
  return groups
})

const todayIndex = computed(() => {
  const today = dayjs().format('YYYY-MM-DD')
  return daysOfYear.value.findIndex((day) => day.date === today)
})

const showTodayOverlay = computed(() => todayIndex.value >= 0)

const todayOverlayStyle = computed(() => ({
  left: `${LEFT_COLUMN_WIDTH + todayIndex.value * DAY_COLUMN_WIDTH}px`,
  width: `${DAY_COLUMN_WIDTH}px`,
}))

const employeeSearchOptions = computed(() => {
  return props.employees.map((employee) => ({
    value: employee.name,
    label: `${employee.name}: ${employee.employee_name}`,
  }))
})

function naturalCompare(a?: string, b?: string) {
  return String(a || '').localeCompare(String(b || ''), undefined, { numeric: true, sensitivity: 'base' })
}

function sortEmployeesByDepartmentAndId(employees: Employee[]) {
  return [...employees].sort((a, b) => {
    const departmentCompare = naturalCompare(a.department, b.department)
    if (departmentCompare !== 0) return departmentCompare

    return naturalCompare(a.name, b.name)
  })
}

const sortedEmployees = computed(() => sortEmployeesByDepartmentAndId(props.employees || []))

const visibleEmployees = computed(() => {
  if (!employeeSearch.value?.length) return sortedEmployees.value
  const selected = new Set(employeeSearch.value.map((item) => item.value))
  return sortedEmployees.value.filter((employee) => selected.has(employee.name))
})

const projectRows = computed(() => {
  return (events.data?.projectRows || []) as ProjectRow[]
})

type ProjectSpan = {
  start: string
  end: string
  startIndex: number
  days: number
  color?: string
  customerColor?: string | null
  employeeCount: number
  shiftTypes: string[]
  poEntered: boolean
  dsRequested: number
  nsRequested: number
}

type ProjectSegment = {
  key: string
  days: number
  active: boolean
  date?: string
  isMonthStart?: boolean
  isWeekend?: boolean
  isToday?: boolean
  label?: string
  subline?: string
  title?: string
  color?: string
  customerColor?: string | null
  poEntered?: boolean
  dsRequested?: number
  nsRequested?: number
}

function projectKey(project: ProjectRow) {
  return project.project || project.project_name
}

const projectSpans = computed<Record<string, ProjectSpan>>(() => {
  const spans: Record<string, ProjectSpan> = {}

  for (const project of projectRows.value) {
    const dates = Object.keys(project.assignments || {}).sort()
    if (!dates.length) continue

    const employeeSet = new Set<string>()
    const shiftTypeSet = new Set<string>()
    let largestDailyCount = 0

    for (const date of dates) {
      const assignment = project.assignments?.[date]
      largestDailyCount = Math.max(largestDailyCount, Number(assignment?.count || 0))

      for (const employee of assignment?.employees || []) {
        employeeSet.add(employee)
      }

      for (const shiftType of assignment?.shift_types || []) {
        shiftTypeSet.add(shiftType)
      }
    }

    const startIndex = daysOfYear.value.findIndex((day) => day.date === dates[0])
    const endIndex = daysOfYear.value.findIndex((day) => day.date === dates[dates.length - 1])

    spans[projectKey(project)] = {
      start: dates[0],
      end: dates[dates.length - 1],
      startIndex: Math.max(0, startIndex),
      days: Math.max(1, endIndex - startIndex + 1),
      color: project.po_entered === false ? 'red' : 'green',
      customerColor: project.customer_color || null,
      employeeCount: employeeSet.size || largestDailyCount,
      shiftTypes: Array.from(shiftTypeSet).sort(),
      poEntered: project.po_entered !== false,
      dsRequested: Number(project.ds_requested || 0),
      nsRequested: Number(project.ns_requested || 0),
    }
  }

  return spans
})

function projectSpan(project: ProjectRow) {
  return projectSpans.value[projectKey(project)]
}

function projectSpanSubline(_project: ProjectRow, span: ProjectSpan) {
  return `${dayjs(span.start).format('DD MMM')} – ${dayjs(span.end).format('DD MMM')}`
}

function projectSpanTitle(project: ProjectRow, span: ProjectSpan) {
  return [
    project.project_name,
    project.project,
    project.status,
    `${dayjs(span.start).format('DD MMM YYYY')} - ${dayjs(span.end).format('DD MMM YYYY')}`,
    span.poEntered ? 'PO Entered' : 'PO Missing',
    `${span.dsRequested || 0} DS Requested`,
    `${span.nsRequested || 0} NS Requested`,
  ].filter(Boolean).join(' | ')
}

function projectSegments(project: ProjectRow): ProjectSegment[] {
  const span = projectSpan(project)

  if (!span) {
    return daysOfYear.value.map((day) => ({
      key: `${projectKey(project)}-${day.date}`,
      days: 1,
      active: false,
      date: day.date,
      isMonthStart: day.isMonthStart,
      isWeekend: day.isWeekend,
      isToday: day.isToday,
      title: `${project.project_name} | ${dayjs(day.date).format('DD MMM YYYY')}`,
    }))
  }

  const segments: ProjectSegment[] = []

  for (let index = 0; index < daysOfYear.value.length; index++) {
    const day = daysOfYear.value[index]

    if (index === span.startIndex) {
      segments.push({
        key: `${projectKey(project)}-${span.start}-${span.end}`,
        days: span.days,
        active: true,
        date: span.start,
        isMonthStart: day.isMonthStart,
        isToday: daysOfYear.value
          .slice(span.startIndex, span.startIndex + span.days)
          .some((spanDay) => spanDay.isToday),
        label: project.project_name,
        subline: projectSpanSubline(project, span),
        title: projectSpanTitle(project, span),
        color: span.color,
        customerColor: span.customerColor,
        poEntered: span.poEntered,
        dsRequested: span.dsRequested,
        nsRequested: span.nsRequested,
      })
      index += span.days - 1
      continue
    }

    segments.push({
      key: `${projectKey(project)}-${day.date}`,
      days: 1,
      active: false,
      date: day.date,
      isMonthStart: day.isMonthStart,
      isWeekend: day.isWeekend,
      isToday: day.isToday,
      title: `${project.project_name} | ${dayjs(day.date).format('DD MMM YYYY')}`,
    })
  }

  return segments
}

const projectTableMaxHeight = computed(() => {
  const headerHeight = 52
  const rowHeight = 30
  const naturalHeight = headerHeight + projectRows.value.length * rowHeight
  return Math.min(240, Math.max(112, naturalHeight))
})

const employeeTableMaxHeight = computed(() => {
  const total = props.maxHeightPx || 650
  const projectPanelUsed = projectRows.value.length ? projectTableMaxHeight.value + 16 : 0
  return Math.max(220, total - projectPanelUsed)
})

function employeeDisplayName(employee: Employee) {
  return employee.employee_name || [employee.first_name, employee.last_name].filter(Boolean).join(' ') || employee.name
}

function employeeSubline(employee: Employee) {
  return [employee.name, employee.designation].filter(Boolean).join(' · ')
}

function employeeTitle(employee: Employee) {
  return [employee.employee_name, employee.name, employee.designation].filter(Boolean).join(' | ')
}

function isHoliday(event: RawEvent): event is HolidayWithDate {
  return 'holiday' in event
}

function isLeave(event: RawEvent): event is LeaveApplication {
  return 'leave' in event
}

function isShift(event: RawEvent): event is ShiftAssignment {
  return 'shift_type' in event
}

function overlaps(date: Dayjs, startDate?: string | null, endDate?: string | null) {
  if (!startDate) return false
  const start = dayjs(startDate)
  const end = endDate ? dayjs(endDate) : firstOfYear.value.endOf('year')
  return start.isSameOrBefore(date, 'day') && end.isSameOrAfter(date, 'day')
}

function safeColor(color?: string): Color {
  const key = (color || 'gray').toLowerCase() as Color
  const allowed: Color[] = ['blue', 'cyan', 'fuchsia', 'green', 'lime', 'orange', 'pink', 'red', 'violet', 'yellow', 'gray']
  return allowed.includes(key) ? key : 'gray'
}

function palette(color?: string) {
  const key = safeColor(color)
  return ((colors as any)[key] || (colors as any).gray) as Record<string, string>
}

function normaliseHexColor(value?: string | null) {
  if (!value) return ''

  const trimmed = value.trim()
  if (/^#[0-9a-fA-F]{3}$/.test(trimmed) || /^#[0-9a-fA-F]{6}$/.test(trimmed)) return trimmed
  if (/^[0-9a-fA-F]{3}$/.test(trimmed) || /^[0-9a-fA-F]{6}$/.test(trimmed)) return `#${trimmed}`

  return ''
}

function hexToRgb(hex: string) {
  const normalized = normaliseHexColor(hex)
  if (!normalized) return null

  const raw = normalized.slice(1)
  const expanded = raw.length === 3 ? raw.split('').map((char) => char + char).join('') : raw
  const numeric = Number.parseInt(expanded, 16)

  return {
    r: (numeric >> 16) & 255,
    g: (numeric >> 8) & 255,
    b: numeric & 255,
  }
}

function contrastTextColor(hex: string) {
  const rgb = hexToRgb(hex)
  if (!rgb) return (colors as any).gray[800]

  const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000
  return brightness >= 150 ? (colors as any).gray[900] : '#ffffff'
}

function mutedContrastTextColor(hex: string) {
  const textColor = contrastTextColor(hex)
  return textColor === '#ffffff' ? 'rgb(255 255 255 / 0.82)' : 'rgb(55 65 81 / 0.78)'
}

function darkenHexColor(hex: string, amount = 0.28) {
  const rgb = hexToRgb(hex)
  if (!rgb) return normaliseHexColor(hex)

  const clamp = (value: number) => Math.max(0, Math.min(255, Math.round(value)))
  const toHex = (value: number) => clamp(value).toString(16).padStart(2, '0')

  return `#${toHex(rgb.r * (1 - amount))}${toHex(rgb.g * (1 - amount))}${toHex(rgb.b * (1 - amount))}`
}

function formatShift(shift: ShiftAssignment): ShiftAssignment {
  return {
    ...shift,
    color: safeColor(shift.color),
    start_time: shift.start_time ? dayjs(shift.start_time, 'hh:mm:ss').format('HH:mm') : '',
    end_time: shift.end_time ? dayjs(shift.end_time, 'hh:mm:ss').format('HH:mm') : '',
  }
}

function shiftCellLabel(shift: ShiftAssignment) {
  const customerAbbreviation = shift.customer_abbreviation?.trim()

  if (customerAbbreviation) return customerAbbreviation

  // Project-linked shifts should not fall back to the full project name in the
  // compact annual cells. If the Project is missing customer_abbreviation, leave
  // the annual cell blank so the missing abbreviation is obvious.
  if (shift.custom_project) return ''

  // Non-project shift assignments can still show their shift type.
  return shift.shift_type
}

function hasNote(note: string | null | undefined) {
  return typeof note === 'string' && note.trim().length > 0
}

function mapEventsToYear(data: Events): MappedEvents {
  const mappedEvents: MappedEvents = {}

  for (const employee in data) {
    mappedEvents[employee] = {}

    for (const day of daysOfYear.value) {
      const date = dayjs(day.date)
      const shifts: ShiftAssignment[] = []
      let blockedCell: YearCell | null = null

      for (const event of data[employee] || []) {
        if (isHoliday(event) && date.isSame(event.holiday_date, 'day')) {
          blockedCell = {
            type: 'holiday',
            label: event.weekly_off ? 'WO' : 'H',
            title: event.weekly_off ? 'Weekly Off' : event.description,
          }
          break
        }

        if (isLeave(event) && overlaps(date, event.from_date, event.to_date)) {
          blockedCell = {
            type: 'leave',
            label: 'L',
            title: event.leave_type,
          }
          break
        }

        if (isShift(event) && overlaps(date, event.start_date, event.end_date)) {
          shifts.push(formatShift(event))
        }
      }

      if (blockedCell) {
        mappedEvents[employee][day.date] = blockedCell
        continue
      }

      if (shifts.length) {
        shifts.sort((a, b) => (a.start_time || '').localeCompare(b.start_time || ''))
        const firstShift = shifts[0]
        const firstShiftLabel = shiftCellLabel(firstShift)
        mappedEvents[employee][day.date] = {
          type: 'shift',
          label: shifts.length > 1 && firstShiftLabel ? `${firstShiftLabel}+` : firstShiftLabel,
          title: [
            firstShift.customer_abbreviation ? `Customer: ${firstShift.customer_abbreviation}` : '',
            firstShift.custom_project_name,
            firstShift.shift_type,
            firstShift.shift_location,
            firstShift.note ? `Note: ${firstShift.note}` : '',
          ].filter(Boolean).join(' | '),
          shift: firstShift,
          shifts,
        }
      }
    }
  }

  return mappedEvents
}

function getEmployeeCell(employee: string, date: string): YearCell | undefined {
  return events.data?.mappedEvents?.[employee]?.[date]
}

function employeeCellLabel(employee: string, date: string) {
  return getEmployeeCell(employee, date)?.label || ''
}

function employeeCellTitle(employee: string, date: string) {
  return getEmployeeCell(employee, date)?.title || dayjs(date).format('dddd, DD MMMM YYYY')
}

function employeeCellStyle(employee: string, date: string) {
  const cell = getEmployeeCell(employee, date)
  if (!cell) return {}

  if (cell.type === 'holiday') {
    return { backgroundColor: (colors as any).blue[50], color: (colors as any).blue[700] }
  }

  if (cell.type === 'leave') {
    return { backgroundColor: (colors as any).pink[50], color: (colors as any).pink[700] }
  }

  const color = palette(cell.shift.color)
  const borderColor = hasNote(cell.shift.note) ? (colors as any).red[500] : color[300]

  return {
    backgroundColor: color[100],
    borderColor,
    boxShadow: `inset 0 0 0 1px ${borderColor}`,
    color: (colors as any).gray[900],
  }
}

function openEmployeeCell(employee: string, date: string) {
  const cell = getEmployeeCell(employee, date)
  if (cell?.type === 'holiday' || cell?.type === 'leave') return

  selectedCell.value = { employee, date }
  shiftAssignment.value = cell?.type === 'shift' ? cell.shift.name : ''
  showShiftAssignmentDialog.value = true
}

function projectSegmentClass(segment: ProjectSegment) {
  return {
    'year-project-span': segment.active,
    'year-month-start': segment.isMonthStart,
    'year-weekend': segment.isWeekend && !segment.active,
  }
}

function projectSegmentStyle(segment: ProjectSegment) {
  if (!segment.active) return {}

  const customerColor = normaliseHexColor(segment.customerColor)
  if (customerColor) {
    const borderColor = darkenHexColor(customerColor)
    return {
      backgroundColor: customerColor,
      borderColor,
      boxShadow: `inset 0 0 0 1px ${borderColor}`,
      color: contrastTextColor(customerColor),
      '--year-project-span-text': contrastTextColor(customerColor),
      '--year-project-span-muted': mutedContrastTextColor(customerColor),
    }
  }

  const color = palette(segment.poEntered === false ? 'red' : 'green')
  return {
    backgroundColor: color[50],
    borderColor: color[300],
    color: (colors as any).gray[800],
  }
}

function scrollToToday() {
  const today = dayjs().format('YYYY-MM-DD')
  const targetTodayIndex = daysOfYear.value.findIndex((day) => day.date === today)

  if (targetTodayIndex < 0) return false

  const leftOffset = 4 * DAY_COLUMN_WIDTH
  const targetLeft = Math.max(0, targetTodayIndex * DAY_COLUMN_WIDTH - leftOffset)

  if (projectScroller.value) projectScroller.value.scrollLeft = targetLeft
  if (employeeScroller.value) employeeScroller.value.scrollLeft = targetLeft

  emit('hscroll', targetLeft)
  return true
}

watch(
  () => [props.firstOfMonth, props.employeeFilters, props.shiftFilters],
  () => {
    loading.value = true
    events.fetch()
  },
  { deep: true },
)

const events = createResource({
  url: 'hrms.api.roster.get_year_events',
  auto: true,
  makeParams() {
    return {
      year: props.firstOfMonth.year(),
      employee_filters: props.employeeFilters,
      shift_filters: props.shiftFilters,
    }
  },
  transform(data: YearEventsResponse) {
    return {
      mappedEvents: mapEventsToYear(data?.events || {}),
      projectRows: (data?.project_rows || []).sort((a, b) => a.project_name.localeCompare(b.project_name)),
    }
  },
  onSuccess() {
    loading.value = false
  },
  onError(error: { messages?: string[]; message?: string }) {
    loading.value = false
    raiseToast('error', error?.messages?.[0] || error?.message || 'Failed to fetch annual roster')
  },
})

defineExpose({ events, scrollToToday })
</script>

<style scoped>
.year-table-stage {
  position: relative;
  display: inline-block;
  width: max-content;
  min-width: max-content;
}

.year-today-overlay {
  position: absolute;
  top: 0;
  bottom: 0;
  z-index: 1;
  pointer-events: none;
  background: transparent;
  border-left: 2px solid rgb(31 41 55);
  border-right: 2px solid rgb(31 41 55);
  box-sizing: border-box;
}

.year-roster-table {
  table-layout: fixed;
  width: max-content;
  min-width: max-content;
}

.year-day-colgroup,
.year-roster-table .year-day-header,
.year-roster-table .year-cell {
  min-width: 28px !important;
  max-width: 28px !important;
  width: 28px !important;
}

.year-left-colgroup,
.year-roster-table .year-left-col,
.year-roster-table .year-left-header {
  min-width: 300px !important;
  max-width: 300px !important;
  width: 300px !important;
}

.year-roster-table th,
.year-roster-table td {
  height: 26px;
  padding: 0;
  font-size: 10px;
  line-height: 1;
  overflow: hidden;
  white-space: nowrap;
}

.year-left-col,
.year-left-header {
  position: sticky;
  left: 0;
  z-index: 10;
}

.year-left-header {
  top: 0;
  height: 52px;
  z-index: 20;
}

.year-month-header {
  position: sticky;
  top: 0;
  z-index: 6;
  height: 24px;
}

.year-day-header {
  position: sticky;
  top: 24px;
  z-index: 6;
  height: 28px;
}

.year-cell {
  font-weight: 600;
  vertical-align: middle;
}

.year-project-row td {
  height: 30px;
}

.year-project-cell {
  vertical-align: middle;
}

.year-project-span {
  padding: 2px 8px !important;
  border-width: 1px !important;
  border-style: solid !important;
  border-radius: 6px;
}

.year-project-span-content {
  display: flex;
  min-width: 0;
  height: 100%;
  align-items: center;
  justify-content: center;
  gap: 6px;
  overflow: hidden;
  text-align: left;
  white-space: nowrap;
}

.year-project-status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 13px;
  min-width: 13px;
  height: 13px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.year-project-po-entered {
  color: rgb(22 163 74);
}

.year-project-po-missing {
  color: rgb(239 68 68);
}

.year-project-span-name {
  min-width: 0;
  max-width: 58%;
  color: var(--year-project-span-text, rgb(31 41 55));
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.year-project-span-date {
  min-width: max-content;
  color: var(--year-project-span-muted, rgb(107 114 128));
  font-size: 10px;
  font-weight: 500;
  line-height: 1;
}

.year-project-request {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 13px;
  min-width: 13px;
  height: 13px;
  font-size: 11px;
  line-height: 1;
}

.year-project-request-ds {
  color: rgb(249 115 22);
}

.year-project-request-ns {
  color: rgb(14 165 233);
}

.year-project-request-count {
  min-width: max-content;
  color: var(--year-project-span-muted, rgb(55 65 81));
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
}

.year-cell:hover {
  outline: 1px solid rgb(59 130 246 / 0.6);
  outline-offset: -1px;
}

.year-weekend {
  background-image: linear-gradient(rgb(249 250 251 / 0.7), rgb(249 250 251 / 0.7));
}

.year-month-start {
  border-left-width: 2px !important;
  border-left-color: rgb(156 163 175) !important;
}


.year-dialog-open .year-left-col,
.year-dialog-open .year-left-header,
.year-dialog-open .year-month-header,
.year-dialog-open .year-day-header,
.year-dialog-open .year-today-overlay {
  z-index: 0 !important;
}

.year-employee-search-header {
  height: 86px;
  vertical-align: top;
}

.year-employee-header-content {
  display: flex;
  min-height: 86px;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.year-employee-search {
  width: 100%;
  max-width: 100%;
  line-height: normal;
}

.year-employee-search :deep(input),
.year-employee-search :deep(.input),
.year-employee-search :deep(.form-control) {
  min-height: 26px;
  height: 26px;
  font-size: 11px;
}

.year-employee-legend-title {
  margin-top: 1px;
  color: rgb(107 114 128);
  font-size: 9px;
  font-weight: 600;
  line-height: 1;
}

.year-employee-legend {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 8px;
}

.year-employee-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  color: rgb(107 114 128);
  font-size: 9px;
  line-height: 1.05;
  white-space: nowrap;
}

.year-employee-legend-dot {
  display: inline-block;
  width: 9px;
  min-width: 9px;
  height: 9px;
  border-radius: 9999px;
  border: 1px solid rgb(107 114 128 / 0.4);
}

.year-employee-legend-fifo {
  background: rgb(250 204 21);
}

.year-employee-legend-ds {
  background: rgb(34 197 94);
}

.year-employee-legend-ns {
  background: rgb(59 130 246);
}

.year-employee-legend-pth {
  background: rgb(168 85 247);
}


.year-project-legend-header {
  height: 74px;
  vertical-align: top;
}

.year-project-header-content {
  line-height: 1.1;
}

.year-project-header-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  color: rgb(107 114 128);
  font-size: 12px;
}

.year-project-legend {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 8px;
}

.year-project-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  color: rgb(107 114 128);
  font-size: 9px;
  line-height: 1.05;
  white-space: nowrap;
}

.year-legend-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 11px;
  min-width: 11px;
  height: 11px;
  border-radius: 9999px;
  font-size: 9px;
  line-height: 1;
}

.year-legend-po-entered {
  color: rgb(34 197 94);
}

.year-legend-po-missing {
  color: rgb(239 68 68);
}

.year-legend-ds-requested {
  color: rgb(249 115 22);
}

.year-legend-ns-requested {
  color: rgb(14 165 233);
}

</style>
