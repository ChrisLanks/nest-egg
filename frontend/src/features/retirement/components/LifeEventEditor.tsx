/**
 * Modal for creating or editing a life event.
 */

import {
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  NumberInput,
  NumberInputField,
  Select,
  Switch,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useEffect, useState } from 'react';
import type { LifeEvent, LifeEventCategory, LifeEventCreate } from '../types/retirement';

const CATEGORY_OPTIONS: { value: LifeEventCategory; label: string }[] = [
  { value: 'child', label: 'Child' },
  { value: 'pet', label: 'Pet' },
  { value: 'home_purchase', label: 'Home Purchase' },
  { value: 'home_downsize', label: 'Home Downsize' },
  { value: 'career_change', label: 'Career Change' },
  { value: 'bonus', label: 'Bonus / Windfall' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'travel', label: 'Travel' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'elder_care', label: 'Elder Care' },
  { value: 'custom', label: 'Custom' },
];

interface LifeEventEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (event: LifeEventCreate) => void;
  existingEvent?: LifeEvent | null;
  isLoading?: boolean;
}

export function LifeEventEditor({
  isOpen,
  onClose,
  onSave,
  existingEvent,
  isLoading,
}: LifeEventEditorProps) {
  const [name, setName] = useState('');
  const [category, setCategory] = useState<LifeEventCategory>('custom');
  const [startAge, setStartAge] = useState(65);
  const [endAge, setEndAge] = useState<number | null>(null);
  const [annualCost, setAnnualCost] = useState<number | null>(null);
  const [oneTimeCost, setOneTimeCost] = useState<number | null>(null);
  const [incomeChange, setIncomeChange] = useState<number | null>(null);
  const [useMedicalInflation, setUseMedicalInflation] = useState(false);

  useEffect(() => {
    if (existingEvent) {
      setName(existingEvent.name);
      setCategory(existingEvent.category);
      setStartAge(existingEvent.start_age);
      setEndAge(existingEvent.end_age);
      setAnnualCost(existingEvent.annual_cost);
      setOneTimeCost(existingEvent.one_time_cost);
      setIncomeChange(existingEvent.income_change);
      setUseMedicalInflation(existingEvent.use_medical_inflation);
    } else {
      setName('');
      setCategory('custom');
      setStartAge(65);
      setEndAge(null);
      setAnnualCost(null);
      setOneTimeCost(null);
      setIncomeChange(null);
      setUseMedicalInflation(false);
    }
  }, [existingEvent, isOpen]);

  const handleSave = useCallback(() => {
    const event: LifeEventCreate = {
      name,
      category,
      start_age: startAge,
      end_age: endAge,
      annual_cost: annualCost,
      one_time_cost: oneTimeCost,
      income_change: incomeChange,
      use_medical_inflation: useMedicalInflation,
    };
    onSave(event);
  }, [name, category, startAge, endAge, annualCost, oneTimeCost, incomeChange, useMedicalInflation, onSave]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{existingEvent ? 'Edit Life Event' : 'Add Life Event'}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel fontSize="sm">Name</FormLabel>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Kids' College"
                size="sm"
              />
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Category</FormLabel>
              <Select
                value={category}
                onChange={(e) => setCategory(e.target.value as LifeEventCategory)}
                size="sm"
              >
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            </FormControl>

            <HStack w="full">
              <FormControl isRequired>
                <FormLabel fontSize="sm">Start Age</FormLabel>
                <NumberInput
                  value={startAge}
                  min={0}
                  max={120}
                  onChange={(_, val) => !isNaN(val) && setStartAge(val)}
                  size="sm"
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">End Age</FormLabel>
                <NumberInput
                  value={endAge ?? ''}
                  min={0}
                  max={120}
                  onChange={(_, val) => setEndAge(isNaN(val) ? null : val)}
                  size="sm"
                >
                  <NumberInputField placeholder="One-time" />
                </NumberInput>
              </FormControl>
            </HStack>

            <FormControl>
              <FormLabel fontSize="sm">Annual Cost ($)</FormLabel>
              <NumberInput
                value={annualCost ?? ''}
                min={0}
                step={1000}
                onChange={(_, val) => setAnnualCost(isNaN(val) ? null : val)}
                size="sm"
              >
                <NumberInputField placeholder="Recurring yearly cost" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">One-Time Cost ($)</FormLabel>
              <NumberInput
                value={oneTimeCost ?? ''}
                min={0}
                step={1000}
                onChange={(_, val) => setOneTimeCost(isNaN(val) ? null : val)}
                size="sm"
              >
                <NumberInputField placeholder="Lump sum at start age" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Income Change ($)</FormLabel>
              <NumberInput
                value={incomeChange ?? ''}
                step={1000}
                onChange={(_, val) => setIncomeChange(isNaN(val) ? null : val)}
                size="sm"
              >
                <NumberInputField placeholder="Positive = income, negative = loss" />
              </NumberInput>
            </FormControl>

            <FormControl display="flex" alignItems="center">
              <FormLabel fontSize="sm" mb={0}>
                Use Medical Inflation
              </FormLabel>
              <Switch
                isChecked={useMedicalInflation}
                onChange={(e) => setUseMedicalInflation(e.target.checked)}
                size="sm"
              />
            </FormControl>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose} size="sm">
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSave}
            isLoading={isLoading}
            isDisabled={!name || !startAge}
            size="sm"
          >
            {existingEvent ? 'Update' : 'Add'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
