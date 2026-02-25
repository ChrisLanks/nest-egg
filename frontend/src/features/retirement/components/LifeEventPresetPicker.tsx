/**
 * Grid of preset life event cards for quick addition.
 */

import {
  Box,
  Button,
  Grid,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useMemo } from 'react';
import { useLifeEventPresets } from '../hooks/useRetirementScenarios';
import type { LifeEventPreset } from '../types/retirement';

const CATEGORY_COLORS: Record<string, string> = {
  child: 'pink',
  pet: 'orange',
  home_purchase: 'teal',
  home_downsize: 'cyan',
  career_change: 'purple',
  bonus: 'green',
  healthcare: 'red',
  travel: 'blue',
  vehicle: 'gray',
  elder_care: 'yellow',
  custom: 'gray',
};

const CATEGORY_ICONS: Record<string, string> = {
  child: '\uD83D\uDC76',
  pet: '\uD83D\uDC3E',
  home_purchase: '\uD83C\uDFE0',
  home_downsize: '\uD83C\uDFE1',
  career_change: '\uD83D\uDCBC',
  bonus: '\uD83D\uDCB0',
  healthcare: '\uD83C\uDFE5',
  travel: '\u2708\uFE0F',
  vehicle: '\uD83D\uDE97',
  elder_care: '\uD83E\uDDD3',
  custom: '\u2699\uFE0F',
};

interface LifeEventPresetPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPreset: (presetKey: string) => void;
  isLoading?: boolean;
}

export function LifeEventPresetPicker({
  isOpen,
  onClose,
  onSelectPreset,
  isLoading,
}: LifeEventPresetPickerProps) {
  const { data: presets } = useLifeEventPresets();
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Group presets by category
  const groupedPresets = useMemo(() => {
    if (!presets) return {};
    const groups: Record<string, LifeEventPreset[]> = {};
    for (const p of presets) {
      const cat = p.category;
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(p);
    }
    return groups;
  }, [presets]);

  const handleSelect = useCallback(
    (key: string) => {
      onSelectPreset(key);
    },
    [onSelectPreset]
  );

  const formatCost = (preset: LifeEventPreset) => {
    if (preset.annual_cost) return `$${(preset.annual_cost / 1000).toFixed(0)}K/yr`;
    if (preset.one_time_cost) return `$${(preset.one_time_cost / 1000).toFixed(0)}K`;
    if (preset.income_change) {
      const sign = preset.income_change > 0 ? '+' : '';
      return `${sign}$${(preset.income_change / 1000).toFixed(0)}K`;
    }
    return '';
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent maxW="700px">
        <ModalHeader>Add Life Event</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack spacing={4} align="stretch">
            {Object.entries(groupedPresets).map(([category, categoryPresets]) => (
              <Box key={category}>
                <Text
                  fontSize="xs"
                  fontWeight="bold"
                  textTransform="uppercase"
                  color="gray.500"
                  mb={2}
                  letterSpacing="wide"
                >
                  {CATEGORY_ICONS[category] || ''}{' '}
                  {category.replace(/_/g, ' ')}
                </Text>
                <Grid templateColumns="repeat(auto-fill, minmax(200px, 1fr))" gap={2}>
                  {categoryPresets.map((preset) => (
                    <Button
                      key={preset.key}
                      onClick={() => handleSelect(preset.key)}
                      isLoading={isLoading}
                      variant="outline"
                      size="sm"
                      h="auto"
                      py={2}
                      px={3}
                      borderColor={borderColor}
                      bg={cardBg}
                      justifyContent="flex-start"
                      textAlign="left"
                      whiteSpace="normal"
                    >
                      <VStack align="start" spacing={0}>
                        <Text fontSize="sm" fontWeight="medium">
                          {preset.name}
                        </Text>
                        <Text fontSize="xs" color={`${CATEGORY_COLORS[category] || 'gray'}.500`}>
                          {formatCost(preset)}
                          {preset.duration_years ? ` for ${preset.duration_years}yr` : ''}
                        </Text>
                      </VStack>
                    </Button>
                  ))}
                </Grid>
              </Box>
            ))}

            <Button
              variant="outline"
              colorScheme="gray"
              size="sm"
              onClick={onClose}
              mt={2}
            >
              Create Custom Event Instead
            </Button>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
