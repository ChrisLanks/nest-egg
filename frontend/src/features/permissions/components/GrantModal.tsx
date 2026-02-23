/**
 * GrantModal — create or edit a permission grant.
 *
 * Steps:
 *   1. Pick a household member (grantee)
 *   2. Pick a resource type (or "all resources")
 *   3. Check allowed actions (read / create / edit / delete)
 *   4. Optional expiry date
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

const ACTION_LABELS: Record<GrantAction, string> = {
  read: 'View',
  create: 'Create',
  update: 'Edit',
  delete: 'Delete',
};

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
  const [resourceType, setResourceType] = useState<ResourceType>(
    (editGrant?.resource_type as ResourceType) ?? 'account',
  );
  const [actions, setActions] = useState<GrantAction[]>(
    editGrant?.actions ?? ['read'],
  );
  const [expiresAt, setExpiresAt] = useState<string>(
    editGrant?.expires_at ? editGrant.expires_at.split('T')[0] : '',
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['permissions', 'given'] });
    queryClient.invalidateQueries({ queryKey: ['permissions', 'audit'] });
  };

  const createMutation = useMutation({
    mutationFn: (payload: Parameters<typeof permissionsApi.createGrant>[0]) =>
      permissionsApi.createGrant(payload),
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
    if (actions.length === 0) e.actions = 'Select at least one permission';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = () => {
    if (!validate()) return;
    const payload = {
      actions,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
    };
    if (editGrant) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate({
        grantee_id: granteeId,
        resource_type: resourceType,
        ...payload,
      });
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

            {!editGrant && (
              <FormControl isRequired>
                <FormLabel>Resource type</FormLabel>
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

            <FormControl isRequired isInvalid={!!errors.actions}>
              <FormLabel>Permissions</FormLabel>
              <CheckboxGroup
                value={actions}
                onChange={(vals) => setActions(vals as GrantAction[])}
              >
                <HStack spacing={4} wrap="wrap">
                  {(Object.keys(ACTION_LABELS) as GrantAction[]).map((a) => (
                    <Checkbox key={a} value={a}>
                      {ACTION_LABELS[a]}
                    </Checkbox>
                  ))}
                </HStack>
              </CheckboxGroup>
              <FormErrorMessage>{errors.actions}</FormErrorMessage>
            </FormControl>

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
            {editGrant ? 'Save Changes' : 'Grant Access'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
