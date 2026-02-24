/**
 * GrantModal — create or edit a permission grant.
 *
 * Design:
 *   - Read access is always included in submitted grants (household members have
 *     implicit read; an explicit grant makes it show in the permission banner).
 *   - Write actions (Create / Edit / Delete) are opt-in.
 *   - Scope: "Specific Section" grants one resource type; "All Sections" creates
 *     a grant for every resource type in a single operation.
 *   - "Full Edit" preset selects all three write actions at once.
 */

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Button,
  FormControl,
  FormLabel,
  Select,
  CheckboxGroup,
  Checkbox,
  VStack,
  HStack,
  Input,
  FormErrorMessage,
  Text,
  Divider,
  RadioGroup,
  Radio,
  Stack,
  ButtonGroup,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { permissionsApi } from '../api/permissionsApi';
import type {
  GrantAction,
  PermissionGrant,
  ResourceType,
} from '../api/permissionsApi';

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  account: 'Accounts',
  transaction: 'Transactions',
  bill: 'Bills',
  holding: 'Investments / Holdings',
  budget: 'Budgets',
  category: 'Categories',
  rule: 'Transaction Rules',
  savings_goal: 'Savings Goals',
  contribution: 'Contributions',
  recurring_transaction: 'Recurring Transactions',
  report: 'Reports',
  org_settings: 'Household Settings',
};

/** All grantable resource types (matches backend RESOURCE_TYPES). */
const ALL_RESOURCE_TYPES = Object.keys(RESOURCE_TYPE_LABELS) as ResourceType[];

/** Write-only actions shown in the UI — read is always included in the payload. */
const WRITE_ACTIONS: { value: Exclude<GrantAction, 'read'>; label: string }[] = [
  { value: 'create', label: 'Create' },
  { value: 'update', label: 'Edit' },
  { value: 'delete', label: 'Delete' },
];

interface GrantModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Pre-fill form when editing an existing grant */
  editGrant?: PermissionGrant;
}

export const GrantModal = ({ isOpen, onClose, editGrant }: GrantModalProps) => {
  const queryClient = useQueryClient();

  const { data: members = [] } = useQuery({
    queryKey: ['permissions', 'members'],
    queryFn: () => permissionsApi.listMembers(),
    enabled: isOpen,
  });

  const [granteeId, setGranteeId] = useState<string>(editGrant?.grantee_id ?? '');
  const [scope, setScope] = useState<'specific' | 'all'>('specific');
  const [resourceType, setResourceType] = useState<ResourceType>(
    (editGrant?.resource_type as ResourceType) ?? 'account',
  );
  // Write actions only — read is always prepended before submission
  const [writeActions, setWriteActions] = useState<Exclude<GrantAction, 'read'>[]>(() => {
    if (!editGrant) return [];
    return editGrant.actions.filter((a) => a !== 'read') as Exclude<GrantAction, 'read'>[];
  });
  const [expiresAt, setExpiresAt] = useState<string>(
    editGrant?.expires_at ? editGrant.expires_at.split('T')[0] : '',
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['permissions', 'given'] });
    queryClient.invalidateQueries({ queryKey: ['permissions', 'audit'] });
    queryClient.invalidateQueries({ queryKey: ['permissions', 'received'] });
  };

  const createMutation = useMutation({
    mutationFn: async (payload: {
      scope: 'specific' | 'all';
      grantee_id: string;
      resource_type: ResourceType;
      actions: GrantAction[];
      expires_at: string | null;
    }) => {
      if (payload.scope === 'all') {
        await Promise.all(
          ALL_RESOURCE_TYPES.map((rt) =>
            permissionsApi.createGrant({
              grantee_id: payload.grantee_id,
              resource_type: rt,
              actions: payload.actions,
              expires_at: payload.expires_at,
            }),
          ),
        );
      } else {
        await permissionsApi.createGrant({
          grantee_id: payload.grantee_id,
          resource_type: payload.resource_type,
          actions: payload.actions,
          expires_at: payload.expires_at,
        });
      }
    },
    onSuccess: () => {
      invalidate();
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof permissionsApi.updateGrant>[1]) =>
      permissionsApi.updateGrant(editGrant!.id, payload),
    onSuccess: () => {
      invalidate();
      onClose();
    },
  });

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!granteeId) e.granteeId = 'Please select a household member';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = () => {
    if (!validate()) return;

    // Always include 'read' in the submitted actions
    const actions: GrantAction[] = ['read', ...writeActions];
    const expires_at = expiresAt ? new Date(expiresAt).toISOString() : null;

    if (editGrant) {
      updateMutation.mutate({ actions, expires_at });
    } else {
      createMutation.mutate({ scope, grantee_id: granteeId, resource_type: resourceType, actions, expires_at });
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;
  const serverError =
    (createMutation.error as any)?.response?.data?.detail ||
    (updateMutation.error as any)?.response?.data?.detail;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{editGrant ? 'Edit Grant' : 'Grant Access'}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            {serverError && (
              <Text color="red.600" fontSize="sm">
                {serverError}
              </Text>
            )}

            {!editGrant && (
              <FormControl isRequired isInvalid={!!errors.granteeId}>
                <FormLabel>Household member</FormLabel>
                <Select
                  placeholder="Select a member…"
                  value={granteeId}
                  onChange={(e) => setGranteeId(e.target.value)}
                >
                  {members.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.display_name ||
                        [m.first_name, m.last_name].filter(Boolean).join(' ') ||
                        m.email}
                    </option>
                  ))}
                </Select>
                <FormErrorMessage>{errors.granteeId}</FormErrorMessage>
              </FormControl>
            )}

            {/* Scope toggle: specific section vs all sections (create only) */}
            {!editGrant && (
              <FormControl isRequired>
                <FormLabel>Sections</FormLabel>
                <RadioGroup value={scope} onChange={(v) => setScope(v as 'specific' | 'all')}>
                  <Stack direction="row" spacing={4}>
                    <Radio value="specific">Specific section</Radio>
                    <Radio value="all">All sections</Radio>
                  </Stack>
                </RadioGroup>
              </FormControl>
            )}

            {/* Section picker (create + specific scope only) */}
            {!editGrant && scope === 'specific' && (
              <FormControl isRequired>
                <FormLabel>Section</FormLabel>
                <Select
                  value={resourceType}
                  onChange={(e) => setResourceType(e.target.value as ResourceType)}
                >
                  {Object.entries(RESOURCE_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </FormControl>
            )}

            <Divider />

            {/* Write-actions checkboxes + presets */}
            <FormControl>
              <HStack justify="space-between" mb={2}>
                <FormLabel mb={0}>Write permissions</FormLabel>
                <ButtonGroup size="xs" variant="outline">
                  <Button
                    colorScheme={writeActions.length === 3 ? 'brand' : undefined}
                    onClick={() => setWriteActions(['create', 'update', 'delete'])}
                  >
                    Full Edit
                  </Button>
                  <Button onClick={() => setWriteActions([])}>Read Only</Button>
                </ButtonGroup>
              </HStack>
              <Text fontSize="xs" color="text.muted" mb={2}>
                Read access is always included. Select extra write permissions below.
              </Text>
              <CheckboxGroup
                value={writeActions}
                onChange={(vals) =>
                  setWriteActions(vals as Exclude<GrantAction, 'read'>[])
                }
              >
                <HStack spacing={4} wrap="wrap">
                  {WRITE_ACTIONS.map(({ value, label }) => (
                    <Checkbox key={value} value={value}>
                      {label}
                    </Checkbox>
                  ))}
                </HStack>
              </CheckboxGroup>
            </FormControl>

            {/* Optional expiry */}
            <FormControl>
              <FormLabel>Expires on (optional)</FormLabel>
              <Input
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
              />
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose} isDisabled={isLoading}>
            Cancel
          </Button>
          <Button colorScheme="brand" onClick={handleSubmit} isLoading={isLoading}>
            {editGrant
              ? 'Save Changes'
              : scope === 'all'
              ? 'Grant All Sections'
              : 'Grant Access'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
