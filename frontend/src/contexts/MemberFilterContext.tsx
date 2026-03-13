/**
 * Global member filter context.
 *
 * Holds the Set<string> of selected household member IDs so the selection
 * persists across tab / page navigation. All pages that use
 * `useMultiMemberFilter()` share this single state.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useUserView } from "./UserViewContext";
import {
  useHouseholdMembers,
  type HouseholdMember,
} from "../hooks/useHouseholdMembers";

interface MemberFilterContextType {
  selectedIds: Set<string>;
  setSelectedIds: (ids: Set<string>) => void;
  members: HouseholdMember[];
}

const MemberFilterContext = createContext<MemberFilterContextType | undefined>(
  undefined,
);

export function MemberFilterProvider({ children }: { children: ReactNode }) {
  const { isCombinedView } = useUserView();
  const { data: members = [] } = useHouseholdMembers();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Reset to "all" whenever members load or combined view changes
  /* eslint-disable react-hooks/set-state-in-effect -- intentional: sync selection to member/view changes */
  useEffect(() => {
    if (members.length > 0) {
      setSelectedIds(new Set(members.map((m) => m.id)));
    }
  }, [members, isCombinedView]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const value = useMemo(
    () => ({ selectedIds, setSelectedIds, members }),
    [selectedIds, members],
  );

  return (
    <MemberFilterContext.Provider value={value}>
      {children}
    </MemberFilterContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useMemberFilterContext() {
  const ctx = useContext(MemberFilterContext);
  if (!ctx) {
    throw new Error(
      "useMemberFilterContext must be used within MemberFilterProvider",
    );
  }
  return ctx;
}
