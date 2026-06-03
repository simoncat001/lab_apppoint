export const TIME_GRID_STEP_MINUTES = 15
export const HOURLY_SELECTION_STEP_MINUTES = 60

export const isCountBasedPriceType = (priceType?: number | null) => Number(priceType ?? 1) === 0

export const isHourlyPriceType = (priceType?: number | null) => !isCountBasedPriceType(priceType)

export const getTimeGridSelectionStepMinutes = (requiresWholeHourSelection: boolean) => {
  return requiresWholeHourSelection ? HOURLY_SELECTION_STEP_MINUTES : TIME_GRID_STEP_MINUTES
}

export const ceilMinuteToStep = (minute: number, step: number) => {
  if (minute <= 0) return 0
  return Math.min(1440, Math.max(0, Math.ceil(minute / step) * step))
}

export const isWholeHourBoundary = (minute: number) => minute % HOURLY_SELECTION_STEP_MINUTES === 0

export const isTimeGridSelectionRangeValid = (
  range: [number, number],
  requiresWholeHourSelection: boolean,
) => {
  if (range[1] <= range[0]) return false
  if (!requiresWholeHourSelection) return true
  return (
    isWholeHourBoundary(range[0]) &&
    isWholeHourBoundary(range[1]) &&
    (range[1] - range[0]) % HOURLY_SELECTION_STEP_MINUTES === 0
  )
}

export const getNormalizedTimeGridDuration = (
  duration: number,
  requiresWholeHourSelection: boolean,
) => {
  const minimumDuration = getTimeGridSelectionStepMinutes(requiresWholeHourSelection)
  if (!requiresWholeHourSelection) {
    return Math.max(duration, minimumDuration)
  }
  return Math.max(
    minimumDuration,
    Math.ceil(Math.max(duration, minimumDuration) / HOURLY_SELECTION_STEP_MINUTES) *
      HOURLY_SELECTION_STEP_MINUTES,
  )
}

type TimeGridBoundaryInput = {
  anchorStart: number | null
  startMin: number
  endMin: number
  requiresWholeHourSelection: boolean
}

export const isSelectableTimeGridBoundary = ({
  anchorStart,
  startMin,
  endMin,
  requiresWholeHourSelection,
}: TimeGridBoundaryInput) => {
  if (!requiresWholeHourSelection) return true
  if (anchorStart === null) return isWholeHourBoundary(startMin)
  if (startMin < anchorStart) return isWholeHourBoundary(startMin)
  if (startMin === anchorStart) return true
  return isWholeHourBoundary(startMin) || endMin === 1440
}

export const buildTimeGridSelectionRange = ({
  anchorStart,
  startMin,
  endMin,
  requiresWholeHourSelection,
}: Omit<TimeGridBoundaryInput, 'anchorStart'> & { anchorStart: number }) => {
  if (!requiresWholeHourSelection) {
    return [Math.min(anchorStart, startMin), Math.max(anchorStart + TIME_GRID_STEP_MINUTES, endMin)] as [
      number,
      number,
    ]
  }

  if (startMin < anchorStart) {
    if (!isWholeHourBoundary(startMin)) return null
    return [startMin, anchorStart] as [number, number]
  }

  if (startMin === anchorStart) {
    return [anchorStart, Math.min(anchorStart + HOURLY_SELECTION_STEP_MINUTES, 1440)] as [number, number]
  }

  if (isWholeHourBoundary(startMin)) {
    return [anchorStart, startMin] as [number, number]
  }

  if (endMin === 1440) {
    return [anchorStart, 1440] as [number, number]
  }

  return null
}
