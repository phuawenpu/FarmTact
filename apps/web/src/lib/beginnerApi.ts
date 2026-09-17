import { mutationRequest, request } from './api'
import type { BeginnerJourney } from './beginner'

export const beginnerApi = {
  list: () => request<{ journeys: BeginnerJourney[] }>('/beginner-journeys'),
  create: (lessonId: 'first_delivery' | 'two_orders' = 'first_delivery') =>
    mutationRequest<BeginnerJourney>('/beginner-journeys', { lesson_id: lessonId }),
  get: (id: string) => request<BeginnerJourney>(`/beginner-journeys/${encodeURIComponent(id)}`),
  action: (journey: Pick<BeginnerJourney, 'id' | 'revision'>, actionId: string, optionId?: string) =>
    mutationRequest<BeginnerJourney>(`/beginner-journeys/${encodeURIComponent(journey.id)}/actions`, {
      revision: journey.revision, action_id: actionId, ...(optionId ? { option_id: optionId } : {}),
    }),
}
