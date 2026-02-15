/**
 * Savings Goals page - manage all savings goals
 */

import {
  Box,
  Button,
  Heading,
  HStack,
  SimpleGrid,
  Text,
  VStack,
  useDisclosure,
  Spinner,
  Center,
  Badge,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { savingsGoalsApi } from '../api/savings-goals';
import type { SavingsGoal } from '../types/savings-goal';
import GoalCard from '../features/goals/components/GoalCard';
import GoalForm from '../features/goals/components/GoalForm';

export default function SavingsGoalsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedGoal, setSelectedGoal] = useState<SavingsGoal | null>(null);

  // Get all goals
  const { data: goals = [], isLoading } = useQuery({
    queryKey: ['goals'],
    queryFn: () => savingsGoalsApi.getAll(),
  });

  const handleEdit = (goal: SavingsGoal) => {
    setSelectedGoal(goal);
    onOpen();
  };

  const handleCreate = () => {
    setSelectedGoal(null);
    onOpen();
  };

  const handleClose = () => {
    setSelectedGoal(null);
    onClose();
  };

  const activeGoals = goals.filter(g => !g.is_completed);
  const completedGoals = goals.filter(g => g.is_completed);

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">Savings Goals</Heading>
            <Text color="gray.600">
              Track progress toward your financial goals
            </Text>
          </VStack>
          <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={handleCreate}>
            New Goal
          </Button>
        </HStack>

        {/* Loading state */}
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Empty state */}
        {!isLoading && goals.length === 0 && (
          <Center py={12}>
            <VStack spacing={4}>
              <Text fontSize="lg" color="gray.500">
                No savings goals yet
              </Text>
              <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={handleCreate}>
                Create Your First Goal
              </Button>
            </VStack>
          </Center>
        )}

        {/* Goals tabs */}
        {!isLoading && goals.length > 0 && (
          <Tabs variant="enclosed" colorScheme="brand">
            <TabList>
              <Tab>
                Active Goals{' '}
                <Badge ml={2} colorScheme="blue">
                  {activeGoals.length}
                </Badge>
              </Tab>
              <Tab>
                Completed Goals{' '}
                <Badge ml={2} colorScheme="green">
                  {completedGoals.length}
                </Badge>
              </Tab>
            </TabList>

            <TabPanels>
              {/* Active goals */}
              <TabPanel>
                {activeGoals.length === 0 ? (
                  <Center py={8}>
                    <Text color="gray.500">No active goals</Text>
                  </Center>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                    {activeGoals.map((goal) => (
                      <GoalCard key={goal.id} goal={goal} onEdit={handleEdit} />
                    ))}
                  </SimpleGrid>
                )}
              </TabPanel>

              {/* Completed goals */}
              <TabPanel>
                {completedGoals.length === 0 ? (
                  <Center py={8}>
                    <Text color="gray.500">No completed goals yet</Text>
                  </Center>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                    {completedGoals.map((goal) => (
                      <GoalCard key={goal.id} goal={goal} onEdit={handleEdit} />
                    ))}
                  </SimpleGrid>
                )}
              </TabPanel>
            </TabPanels>
          </Tabs>
        )}
      </VStack>

      {/* Goal form modal */}
      <GoalForm isOpen={isOpen} onClose={handleClose} goal={selectedGoal} />
    </Box>
  );
}
