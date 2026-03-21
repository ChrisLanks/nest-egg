/**
 * Zustand store for guest household context.
 *
 * When activeHouseholdId is set, the API interceptor injects
 * X-Household-Id on every request so the backend scopes data
 * to the guest household.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import api, { registerHouseholdGetter } from "../services/api";

export interface GuestHousehold {
  organization_id: string;
  organization_name: string;
  role: "viewer" | "advisor";
  label: string | null;
  is_active: boolean;
}

interface HouseholdState {
  /** null = viewing home household */
  activeHouseholdId: string | null;
  activeHouseholdName: string | null;
  guestHouseholds: GuestHousehold[];
  isGuest: boolean;
  guestRole: "viewer" | "advisor" | null;
  setActiveHousehold: (id: string | null, name?: string | null) => void;
  fetchGuestHouseholds: () => Promise<void>;
  reset: () => void;
}

export const useHouseholdStore = create<HouseholdState>()(
  persist(
    (set, get) => ({
      activeHouseholdId: null,
      activeHouseholdName: null,
      guestHouseholds: [],
      isGuest: false,
      guestRole: null,

      setActiveHousehold: (id, name = null) => {
        if (!id) {
          set({
            activeHouseholdId: null,
            activeHouseholdName: null,
            isGuest: false,
            guestRole: null,
          });
          return;
        }

        const household = get().guestHouseholds.find(
          (h) => h.organization_id === id,
        );
        set({
          activeHouseholdId: id,
          activeHouseholdName: name || household?.organization_name || null,
          isGuest: true,
          guestRole: household?.role || "viewer",
        });
      },

      fetchGuestHouseholds: async () => {
        try {
          const { data } = await api.get<GuestHousehold[]>(
            "/guest-access/my-households",
          );
          set({ guestHouseholds: data });

          // If the active household was revoked, reset to home
          const activeId = get().activeHouseholdId;
          if (activeId && !data.some((h) => h.organization_id === activeId)) {
            get().setActiveHousehold(null);
          }
        } catch {
          // Silently fail — guest access may not be available
        }
      },

      reset: () =>
        set({
          activeHouseholdId: null,
          activeHouseholdName: null,
          guestHouseholds: [],
          isGuest: false,
          guestRole: null,
        }),
    }),
    {
      name: "nest-egg-active-household",
      partialize: (state) => ({
        activeHouseholdId: state.activeHouseholdId,
        activeHouseholdName: state.activeHouseholdName,
      }),
    },
  ),
);

// Register the getter so the API interceptor can read activeHouseholdId
// without importing this store (avoids circular dependency).
registerHouseholdGetter(() => useHouseholdStore.getState().activeHouseholdId);
