/**
 * User View Toggle Component
 *
 * Checkbox-based dropdown to filter household members.
 * - "All Members" checkbox: toggles between combined and filtered view
 * - Individual member checkboxes: toggle specific members on/off
 * - At least one member must remain selected at all times
 *
 * In single-user households the toggle is hidden entirely.
 * On self-only pages (preferences, permissions, household) it is disabled.
 */

import {
  Box,
  Button,
  Checkbox,
  HStack,
  Text,
  Spinner,
  VStack,
} from "@chakra-ui/react";
import { ChevronDownIcon } from "@chakra-ui/icons";
import { useState, useRef, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useAuthStore } from "../features/auth/stores/authStore";
import { useUserView } from "../contexts/UserViewContext";
import { useHouseholdMembers } from "../hooks/useHouseholdMembers";
import type { HouseholdMember } from "../hooks/useHouseholdMembers";

// Pages that always operate on the current user's own data
const SELF_ONLY_PATHS = ["/preferences", "/permissions", "/household"];

export const UserViewToggle = () => {
  const { user } = useAuthStore();
  const {
    selectedMemberIds,
    toggleMember,
    selectAll,
    isAllSelected,
    _registerHouseholdMembers,
    setSelectedMemberIds,
  } = useUserView();
  const { pathname } = useLocation();
  const isSelfOnlyPage = SELF_ONLY_PATHS.includes(pathname);

  // Fetch household members and register them into the context
  const { data: members, isLoading } = useHouseholdMembers();

  // Push loaded members into UserViewContext
  useEffect(() => {
    if (members && members.length > 0) {
      _registerHouseholdMembers(members);
    }
  }, [members, _registerHouseholdMembers]);

  // Dropdown open/close state
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [isOpen]);

  // Don't show toggle if only one member
  if (!isLoading && members && members.length <= 1) {
    return null;
  }

  if (isLoading) {
    return <Spinner size="sm" />;
  }

  // Format display name for a member
  const getDisplayName = (member: HouseholdMember): string => {
    if (member.display_name) return member.display_name;
    if (member.first_name && member.last_name) {
      return `${member.first_name} ${member.last_name}`;
    }
    if (member.first_name) return member.first_name;
    return member.email.split("@")[0];
  };

  // Determine the button label based on selection
  const getButtonLabel = (): string => {
    if (isSelfOnlyPage) return "Self";
    if (isAllSelected) return "All Members";
    if (selectedMemberIds.size === 1) {
      const selectedId = [...selectedMemberIds][0];
      if (selectedId === user?.id) return "Self";
      const member = members?.find((m) => m.id === selectedId);
      return member ? getDisplayName(member) : "Member";
    }
    return `${selectedMemberIds.size} Members`;
  };

  const handleToggleAll = () => {
    if (isAllSelected) {
      // Deselect all → select only self
      if (user?.id) {
        setSelectedMemberIds(new Set([user.id]));
      }
    } else {
      selectAll();
    }
  };

  const handleToggleMember = (memberId: string) => {
    toggleMember(memberId);
  };

  return (
    <Box position="relative" ref={ref}>
      <HStack spacing={2} align="center">
        <Text
          fontSize="sm"
          fontWeight="medium"
          color={isSelfOnlyPage ? "text.muted" : "text.secondary"}
        >
          View:
        </Text>
        <Button
          rightIcon={<ChevronDownIcon />}
          size="sm"
          variant="outline"
          bg="bg.surface"
          width="200px"
          justifyContent="space-between"
          isDisabled={isSelfOnlyPage}
          opacity={isSelfOnlyPage ? 0.5 : 1}
          onClick={() => setIsOpen((prev) => !prev)}
          fontWeight="normal"
        >
          {getButtonLabel()}
        </Button>
      </HStack>

      {isOpen && !isSelfOnlyPage && (
        <Box
          position="absolute"
          top="calc(100% + 4px)"
          right={0}
          bg="bg.surface"
          borderWidth={1}
          borderColor="border.default"
          borderRadius="md"
          boxShadow="md"
          zIndex={200}
          minW="220px"
          py={2}
        >
          <VStack align="stretch" spacing={0}>
            {/* All Members checkbox */}
            <Box
              px={4}
              py={2}
              _hover={{ bg: "bg.subtle" }}
              cursor="pointer"
              borderBottomWidth={1}
              borderColor="border.default"
              onClick={handleToggleAll}
            >
              <Checkbox
                isChecked={isAllSelected}
                isIndeterminate={!isAllSelected && selectedMemberIds.size > 0}
                onChange={handleToggleAll}
                pointerEvents="none"
                size="sm"
              >
                <Text fontSize="sm" fontWeight="semibold">
                  All Members
                </Text>
              </Checkbox>
            </Box>

            {/* Individual member checkboxes */}
            {members?.map((member) => {
              const isChecked = selectedMemberIds.has(member.id);
              const isSelf = member.id === user?.id;
              return (
                <Box
                  key={member.id}
                  px={4}
                  py={1.5}
                  _hover={{ bg: "bg.subtle" }}
                  cursor="pointer"
                  onClick={() => handleToggleMember(member.id)}
                >
                  <Checkbox
                    isChecked={isChecked}
                    onChange={() => handleToggleMember(member.id)}
                    pointerEvents="none"
                    size="sm"
                  >
                    <Text fontSize="sm">
                      {getDisplayName(member)}
                      {isSelf && (
                        <Text as="span" color="text.muted" fontSize="xs" ml={1}>
                          (you)
                        </Text>
                      )}
                    </Text>
                  </Checkbox>
                </Box>
              );
            })}
          </VStack>
        </Box>
      )}
    </Box>
  );
};
