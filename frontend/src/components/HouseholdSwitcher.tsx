/**
 * Household switcher dropdown.
 *
 * Shows "My Household" plus any guest households the user has access to.
 * Selecting a guest household injects X-Household-Id on all API calls
 * and triggers a full data refetch.
 */

import { useEffect, useRef, useState } from "react";
import { Box, Button, HStack, Text, VStack, Badge } from "@chakra-ui/react";
import { ChevronDownIcon } from "@chakra-ui/icons";
import { useQueryClient } from "@tanstack/react-query";
import { useHouseholdStore } from "../stores/householdStore";

export function HouseholdSwitcher() {
  const {
    activeHouseholdId,
    activeHouseholdName,
    guestHouseholds,
    setActiveHousehold,
    fetchGuestHouseholds,
  } = useHouseholdStore();

  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Fetch guest households on mount
  useEffect(() => {
    fetchGuestHouseholds();
  }, [fetchGuestHouseholds]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen]);

  // Don't render if there are no guest households
  if (guestHouseholds.length === 0) return null;

  const handleSelect = (id: string | null, name?: string | null) => {
    setActiveHousehold(id, name);
    setIsOpen(false);
    // Invalidate all queries to refetch with new household context
    queryClient.invalidateQueries();
  };

  return (
    <Box position="relative" ref={ref}>
      <Button
        size="sm"
        variant="outline"
        rightIcon={<ChevronDownIcon />}
        onClick={() => setIsOpen((prev) => !prev)}
        borderColor={activeHouseholdId ? "orange.400" : "border.default"}
        color={activeHouseholdId ? "orange.600" : undefined}
      >
        {activeHouseholdId
          ? activeHouseholdName || "Guest Household"
          : "My Household"}
      </Button>

      {isOpen && (
        <Box
          position="absolute"
          top="calc(100% + 4px)"
          left={0}
          bg="bg.surface"
          borderWidth={1}
          borderColor="border.default"
          borderRadius="md"
          boxShadow="lg"
          zIndex={200}
          minW="220px"
          py={1}
        >
          {/* Home household */}
          <Box
            px={3}
            py={2}
            cursor="pointer"
            bg={!activeHouseholdId ? "bg.subtle" : undefined}
            _hover={{ bg: "bg.subtle" }}
            onClick={() => handleSelect(null)}
          >
            <HStack justify="space-between">
              <Text fontSize="sm" fontWeight="medium">
                My Household
              </Text>
              {!activeHouseholdId && (
                <Badge colorScheme="green" fontSize="2xs">
                  Active
                </Badge>
              )}
            </HStack>
          </Box>

          {/* Divider */}
          <Box borderTopWidth={1} borderColor="border.default" my={1} />

          {/* Guest households */}
          {guestHouseholds.map((h) => (
            <Box
              key={h.organization_id}
              px={3}
              py={2}
              cursor="pointer"
              bg={
                activeHouseholdId === h.organization_id
                  ? "bg.subtle"
                  : undefined
              }
              _hover={{ bg: "bg.subtle" }}
              onClick={() =>
                handleSelect(h.organization_id, h.organization_name)
              }
            >
              <VStack align="start" spacing={0}>
                <HStack justify="space-between" width="full">
                  <Text fontSize="sm" fontWeight="medium">
                    {h.label || h.organization_name}
                  </Text>
                  {activeHouseholdId === h.organization_id && (
                    <Badge colorScheme="orange" fontSize="2xs">
                      Viewing
                    </Badge>
                  )}
                </HStack>
                <HStack spacing={1}>
                  <Badge
                    fontSize="2xs"
                    colorScheme={h.role === "advisor" ? "purple" : "gray"}
                  >
                    {h.role}
                  </Badge>
                  {h.label && h.label !== h.organization_name && (
                    <Text fontSize="xs" color="text.muted">
                      {h.organization_name}
                    </Text>
                  )}
                </HStack>
              </VStack>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
