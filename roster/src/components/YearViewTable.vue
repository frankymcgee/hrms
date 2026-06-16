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
      <div class="year-panel-header flex items-center justify-between border-b bg-gray-50 px-3 py-2">
        <div>
          <div class="text-sm font-semibold text-gray-800">Projects / Planning</div>
          <div class="text-xs text-gray-500">Annual project overview. Employees are not grouped under projects.</div>
        </div>
        <div class="text-xs text-gray-500">{{ projectRows.length }} rows</div>
      </div>

      <div
        ref="projectScroller"
        class="year-roster-scroller overflow-auto"
        :style="{ maxHeight: projectTableMaxHeight + 'px' }"
        @scroll="onProjectScroll"
      >
        <table class="year-roster-table border-separate border-spacing-0">
          <colgroup>
            <col class="year-left-colgroup" />
            <col v-for="day in daysOfYear" :key="`project-col-${day.date}`" class="year-day-colgroup" />
          </colgroup>
          <thead>
            <tr>
              <th rowspan="2" class="year-left-header year-left-col border-b border-r bg-white text-left">
                <div class="px-2 py-1.5 text-xs font-semibold text-gray-700">Project / Planning Row</div>
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
                  'year-today': day.isToday,
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
                v-for="day in daysOfYear"
                :key="`${project.project_name}-${day.date}`"
                class="year-cell year-project-cell border-b border-r text-center"
                :class="[
                  projectCellClass(project, day.date),
                  {
                    'year-month-start': day.isMonthStart,
                    'year-weekend': day.isWeekend,
                    'year-today': day.isToday,
                  },
                ]"
                :style="projectCellStyle(project, day.date)"
                :title="projectCellTitle(project, day.date)"
              ></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Annual employee roster view. This scrolls separately from the project table. -->
    <section class="year-roster-panel year-employee-panel flex min-h-0 flex-1 flex-col rounded-lg border bg-white">
      <div class="year-panel-header flex items-center justify-between gap-4 border-b bg-gray-50 px-3 py-2">
        <div>
          <div class="text-sm font-semibold text-gray-800">Employees</div>
          <div class="text-xs text-gray-500">Annual compact roster grid</div>
        </div>

        <div class="w-[320px] max-w-full">
          <Autocomplete
            :options="employeeSearchOptions"
            v-model="employeeSearch"
            placeholder="Search Employee"
            :multiple="true"
          />
        </div>
      </div>

      <div
        ref="employeeScroller"
        class="year-roster-scroller min-h-0 flex-1 overflow-auto"
        :style="{ maxHeight: employeeTableMaxHeight + 'px' }"
        @scroll="onEmployeeScroll"
      >
        <table class="year-roster-table border-separate border-spacing-0">
          <colgroup>
            <col class="year-left-colgroup" />
            <col v-for="day in daysOfYear" :key="`employee-col-${day.date}`" class="year-day-colgroup" />
          </colgroup>
          <thead>
            <tr>
              <th rowspan="2" class="year-left-header year-left-col border-b border-r bg-white text-left">
                <div class="px-2 py-1.5 text-xs font-semibold text-gray-700">Employee</div>
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
                  'year-today': day.isToday,
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
                  'year-today': day.isToday,
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
  custom_project_name?: string
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

const employeeSearchOptions = computed(() => {
  return props.employees.map((employee) => ({
    value: employee.name,
    label: `${employee.name}: ${employee.employee_name}`,
  }))
})

const visibleEmployees = computed(() => {
  if (!employeeSearch.value?.length) return props.employees
  const selected = new Set(employeeSearch.value.map((item) => item.value))
  return props.employees.filter((employee) => selected.has(employee.name))
})

const projectRows = computed(() => {
  return (events.data?.projectRows || []) as ProjectRow[]
})

type ProjectSpan = {
  start: string
  end: string
  color?: string
}

function projectKey(project: ProjectRow) {
  return project.project || project.project_name
}

const projectSpans = computed<Record<string, ProjectSpan>>(() => {
  const spans: Record<string, ProjectSpan> = {}

  for (const project of projectRows.value) {
    const dates = Object.keys(project.assignments || {}).sort()
    if (!dates.length) continue

    const firstColour = dates
      .map((date) => project.assignments?.[date]?.color)
      .find((color) => !!color)

    spans[projectKey(project)] = {
      start: dates[0],
      end: dates[dates.length - 1],
      color: firstColour || 'green',
    }
  }

  return spans
})

function projectSpan(project: ProjectRow) {
  return projectSpans.value[projectKey(project)]
}

function isProjectSpanActive(project: ProjectRow, date: string) {
  const span = projectSpan(project)
  if (!span) return false
  return date >= span.start && date <= span.end
}

const projectTableMaxHeight = computed(() => {
  const headerHeight = 52
  const rowHeight = 26
  const naturalHeight = headerHeight + projectRows.value.length * rowHeight
  return Math.min(220, Math.max(104, naturalHeight))
})

const employeeTableMaxHeight = computed(() => {
  const total = props.maxHeightPx || 650
  const projectPanelUsed = projectRows.value.length ? projectTableMaxHeight.value + 52 + 16 : 0
  const employeePanelHeader = 52
  return Math.max(220, total - projectPanelUsed - employeePanelHeader)
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

function formatShift(shift: ShiftAssignment): ShiftAssignment {
  return {
    ...shift,
    color: safeColor(shift.color),
    start_time: shift.start_time ? dayjs(shift.start_time, 'hh:mm:ss').format('HH:mm') : '',
    end_time: shift.end_time ? dayjs(shift.end_time, 'hh:mm:ss').format('HH:mm') : '',
  }
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
        mappedEvents[employee][day.date] = {
          type: 'shift',
          label: shifts.length > 1 ? `${firstShift.shift_type}+` : firstShift.shift_type,
          title: [
            firstShift.shift_type,
            firstShift.custom_project_name,
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
  return {
    backgroundColor: color[100],
    borderColor: hasNote(cell.shift.note) ? (colors as any).red[500] : color[300],
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

function projectCellClass(project: ProjectRow, date: string) {
  const span = projectSpan(project)
  if (!span || !isProjectSpanActive(project, date)) return ''

  return {
    'year-project-span': true,
    'year-project-span-start': date === span.start,
    'year-project-span-end': date === span.end,
  }
}

function projectCellTitle(project: ProjectRow, date: string) {
  const span = projectSpan(project)
  if (!span || !isProjectSpanActive(project, date)) {
    return `${project.project_name} | ${dayjs(date).format('DD MMM YYYY')}`
  }

  return [
    project.project_name,
    `${dayjs(span.start).format('DD MMM YYYY')} - ${dayjs(span.end).format('DD MMM YYYY')}`,
  ].filter(Boolean).join(' | ')
}

function projectCellStyle(project: ProjectRow, date: string) {
  const span = projectSpan(project)
  if (!span || !isProjectSpanActive(project, date)) return {}

  const color = palette(span.color)
  return {
    backgroundColor: color[100],
    borderLeftColor: color[100],
    borderRightColor: color[100],
    color: (colors as any).gray[800],
  }
}

function scrollToToday() {
  const today = dayjs().format('YYYY-MM-DD')
  const todayIndex = daysOfYear.value.findIndex((day) => day.date === today)

  if (todayIndex < 0) return false

  const dayWidth = 28
  const leftOffset = 4 * dayWidth
  const targetLeft = Math.max(0, todayIndex * dayWidth - leftOffset)

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
  z-index: 3;
}

.year-left-header {
  top: 0;
  height: 52px;
  z-index: 5;
}

.year-month-header {
  position: sticky;
  top: 0;
  z-index: 2;
  height: 24px;
}

.year-day-header {
  position: sticky;
  top: 24px;
  z-index: 2;
  height: 28px;
}

.year-cell {
  font-weight: 600;
  vertical-align: middle;
}

.year-project-cell {
  font-size: 0;
}

.year-project-span {
  border-right-color: transparent !important;
  border-left-color: transparent !important;
}

.year-project-span-start {
  border-left-color: rgb(156 163 175) !important;
}

.year-project-span-end {
  border-right-color: rgb(156 163 175) !important;
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

.year-today {
  box-shadow: inset 0 0 0 2px rgb(37 99 235 / 0.45);
}

.year-dialog-open .year-left-col,
.year-dialog-open .year-left-header,
.year-dialog-open .year-month-header,
.year-dialog-open .year-day-header {
  z-index: 0 !important;
}
</style>
