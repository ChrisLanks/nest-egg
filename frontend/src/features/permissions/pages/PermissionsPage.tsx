/**
 * PermissionsPage — full access management page.
 *
 * Two tabs:
 *   - "Access I've Granted" — table of active grants I've given, with Edit/Revoke
 *   - "Access I've Received" — read-only table of what others have shared with me
 *
 * Top-right button: "Grant Access" → opens GrantModal
 */

import {
  Box,
  Button,
  Heading,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  HStack,
  Text,
  Spinner,
  Center,
  useDisclosure,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { permissionsApi } from '../api/permissionsApi';
import { GrantList } from '../components/GrantList';
import { GrantModal } from '../components/GrantModal';

export const PermissionsPage = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  const { data: given = [], isLoading: givenLoading } = useQuery({
    queryKey: ['permissions', 'given'],
    queryFn: () => permissionsApi.listGiven(),
  });

  const { data: received = [], isLoading: receivedLoading } = useQuery({
    queryKey: ['permissions', 'received'],
    queryFn: () => permissionsApi.listReceived(),
  });

  const { data: audit = [] } = useQuery({
    queryKey: ['permissions', 'audit'],
    queryFn: () => permissionsApi.listAudit(),
  });

  return (
    <Box p={8} maxW="900px" mx="auto">
      <HStack justify="space-between" mb={6}>
        <Box>
          <Heading size="lg">Permissions</Heading>
          <Text color="gray.600" mt={1} fontSize="sm">
            Control who in your household can view or edit your financial data.
          </Text>
        </Box>
        <Button leftIcon={<AddIcon />} colorScheme="brand" onClick={onOpen}>
          Grant Access
        </Button>
      </HStack>

      <Tabs colorScheme="brand" variant="enclosed">
        <TabList>
          <Tab>Access I've Granted ({given.length})</Tab>
          <Tab>Access I've Received ({received.length})</Tab>
        </TabList>

        <TabPanels>
          <TabPanel px={0} pt={4}>
            {givenLoading ? (
              <Center py={8}>
                <Spinner />
              </Center>
            ) : (
              <GrantList grants={given} mode="given" />
            )}
          </TabPanel>

          <TabPanel px={0} pt={4}>
            {receivedLoading ? (
              <Center py={8}>
                <Spinner />
              </Center>
            ) : (
              <GrantList grants={received} mode="received" />
            )}
          </TabPanel>
        </TabPanels>
      </Tabs>

      {/* Audit log — collapsed by default */}
      {audit.length > 0 && (
        <Box mt={8}>
          <Accordion allowToggle>
            <AccordionItem border="none">
              <AccordionButton
                px={0}
                _hover={{ bg: 'transparent' }}
                color="gray.600"
                fontSize="sm"
              >
                <Box flex={1} textAlign="left" fontWeight="medium">
                  Audit history ({audit.length} events)
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel px={0} pb={0}>
                <Box overflowX="auto">
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #E2E8F0' }}>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: '#718096' }}>
                          When
                        </th>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: '#718096' }}>
                          Event
                        </th>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: '#718096' }}>
                          Resource
                        </th>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: '#718096' }}>
                          Actions before
                        </th>
                        <th style={{ textAlign: 'left', padding: '6px 8px', color: '#718096' }}>
                          Actions after
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {audit.map((e) => (
                        <tr key={e.id} style={{ borderBottom: '1px solid #F7FAFC' }}>
                          <td style={{ padding: '6px 8px', color: '#718096' }}>
                            {new Date(e.occurred_at).toLocaleString()}
                          </td>
                          <td style={{ padding: '6px 8px', fontWeight: 500 }}>{e.action}</td>
                          <td style={{ padding: '6px 8px' }}>{e.resource_type ?? '—'}</td>
                          <td style={{ padding: '6px 8px', color: '#A0AEC0' }}>
                            {e.actions_before?.join(', ') ?? '—'}
                          </td>
                          <td style={{ padding: '6px 8px' }}>
                            {e.actions_after?.join(', ') ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Box>
              </AccordionPanel>
            </AccordionItem>
          </Accordion>
        </Box>
      )}

      <GrantModal isOpen={isOpen} onClose={onClose} />
    </Box>
  );
};
