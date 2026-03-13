/**
 * Multi-select toggle bar for household member filtering.
 *
 * Each member button is independently toggleable. "All" re-selects everyone.
 * Buttons use solid fill when selected, outline when deselected.
 * Uses `Wrap` instead of `isAttached` ButtonGroup to visually signal
 * that multiple buttons can be active simultaneously.
 */

import { Button, HStack, Text, Wrap, WrapItem } from "@chakra-ui/react";
import { FiCheck } from "react-icons/fi";
import type { HouseholdMember } from "../hooks/useHouseholdMembers";

interface MemberMultiSelectProps {
  selectedIds: Set<string>;
  members: HouseholdMember[];
  isAllSelected: boolean;
  onToggle: (memberId: string) => void;
  onSelectAll: () => void;
  label?: string;
  size?: string;
  colorScheme?: string;
}

export function MemberMultiSelect({
  selectedIds,
  members,
  isAllSelected,
  onToggle,
  onSelectAll,
  label = "Members:",
  size = "sm",
  colorScheme = "blue",
}: MemberMultiSelectProps) {
  return (
    <HStack spacing={2} flexWrap="wrap">
      <Text fontSize="sm" fontWeight="medium" color="text.secondary">
        {label}
      </Text>
      <Wrap spacing={1}>
        <WrapItem>
          <Button
            size={size}
            variant={isAllSelected ? "solid" : "outline"}
            colorScheme={isAllSelected ? colorScheme : "gray"}
            onClick={onSelectAll}
          >
            All
          </Button>
        </WrapItem>
        {members.map((member) => {
          const isSelected = selectedIds.has(member.id);
          return (
            <WrapItem key={member.id}>
              <Button
                size={size}
                variant={isSelected ? "solid" : "outline"}
                colorScheme={isSelected ? colorScheme : "gray"}
                onClick={() => onToggle(member.id)}
                leftIcon={isSelected ? <FiCheck /> : undefined}
              >
                {member.display_name ||
                  member.first_name ||
                  member.email.split("@")[0]}
              </Button>
            </WrapItem>
          );
        })}
      </Wrap>
    </HStack>
  );
}
