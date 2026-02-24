/**
 * GrantList — displays a table of active grants.
 * Can show grants I've given (with Edit/Revoke buttons) or grants I've received (read-only).
 */

import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  HStack,
  Button,
  Text,
  IconButton,
  useDisclosure,
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
} from '@chakra-ui/react';
import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { permissionsApi } from '../api/permissionsApi';
import type { PermissionGrant } from '../api/permissionsApi';
import { GrantModal } from './GrantModal';

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  account: 'Accounts',
  transaction: 'Transactions',
  bill: 'Bills',
  holding: 'Investments',
  budget: 'Budgets',
  category: 'Categories',
  rule: 'Rules',
  savings_goal: 'Savings Goals',
  contribution: 'Contributions',
  recurring_transaction: 'Recurring',
  report: 'Reports',
  org_settings: 'Org Settings',
};

const ACTION_COLORS: Record<string, string> = {
  read: 'blue',
  create: 'green',
  update: 'orange',
  delete: 'red',
};

interface GrantListProps {
  grants: PermissionGrant[];
  mode: 'given' | 'received';
}

export const GrantList = ({ grants, mode }: GrantListProps) => {
  const queryClient = useQueryClient();
  const [editTarget, setEditTarget] = useState<PermissionGrant | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<PermissionGrant | null>(null);
  const { isOpen: isEditOpen, onOpen: openEdit, onClose: closeEdit } = useDisclosure();
  const { isOpen: isAlertOpen, onOpen: openAlert, onClose: closeAlert } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);

  const revokeMutation = useMutation({
    mutationFn: (grantId: string) => permissionsApi.revokeGrant(grantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissions', 'given'] });
      queryClient.invalidateQueries({ queryKey: ['permissions', 'audit'] });
      closeAlert();
    },
  });

  if (grants.length === 0) {
    return (
      <Text color="text.muted" py={4}>
        {mode === 'given'
          ? 'You have not granted access to anyone yet.'
          : 'No one has shared access with you yet.'}
      </Text>
    );
  }

  return (
    <>
      <Table variant="simple" size="sm">
        <Thead>
          <Tr>
            <Th>{mode === 'given' ? 'Granted to' : 'Granted by'}</Th>
            <Th>Resource</Th>
            <Th>Permissions</Th>
            <Th>Expires</Th>
            {mode === 'given' && <Th />}
          </Tr>
        </Thead>
        <Tbody>
          {grants.map((g) => {
            const personName =
              mode === 'given' ? g.grantee_display_name : g.grantor_display_name;
            const isExpired = g.expires_at
              ? new Date(g.expires_at) < new Date()
              : false;

            return (
              <Tr key={g.id} opacity={isExpired ? 0.5 : 1}>
                <Td fontWeight="medium">{personName ?? '—'}</Td>
                <Td>{RESOURCE_TYPE_LABELS[g.resource_type] ?? g.resource_type}</Td>
                <Td>
                  <HStack spacing={1} wrap="wrap">
                    {g.actions.filter((a) => a !== 'read').map((a) => (
                      <Badge key={a} colorScheme={ACTION_COLORS[a] ?? 'gray'} size="sm">
                        {a}
                      </Badge>
                    ))}
                    {g.actions.every((a) => a === 'read') && (
                      <Badge colorScheme="gray" size="sm">read only</Badge>
                    )}
                  </HStack>
                </Td>
                <Td>
                  {g.expires_at ? (
                    <Text
                      fontSize="xs"
                      color={isExpired ? 'red.600' : 'text.secondary'}
                    >
                      {isExpired ? 'Expired ' : ''}
                      {new Date(g.expires_at).toLocaleDateString()}
                    </Text>
                  ) : (
                    <Text fontSize="xs" color="text.muted">
                      Never
                    </Text>
                  )}
                </Td>
                {mode === 'given' && (
                  <Td>
                    <HStack spacing={1} justify="flex-end">
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => {
                          setEditTarget(g);
                          openEdit();
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        size="xs"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => {
                          setRevokeTarget(g);
                          openAlert();
                        }}
                      >
                        Revoke
                      </Button>
                    </HStack>
                  </Td>
                )}
              </Tr>
            );
          })}
        </Tbody>
      </Table>

      {/* Edit modal */}
      {editTarget && (
        <GrantModal
          isOpen={isEditOpen}
          onClose={() => {
            closeEdit();
            setEditTarget(null);
          }}
          editGrant={editTarget}
        />
      )}

      {/* Revoke confirmation */}
      <AlertDialog
        isOpen={isAlertOpen}
        leastDestructiveRef={cancelRef}
        onClose={closeAlert}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader>Revoke access</AlertDialogHeader>
            <AlertDialogBody>
              Are you sure? This will immediately remove access for{' '}
              <strong>{revokeTarget?.grantee_display_name ?? 'this user'}</strong>.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={closeAlert}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                ml={3}
                isLoading={revokeMutation.isPending}
                onClick={() => revokeTarget && revokeMutation.mutate(revokeTarget.id)}
              >
                Revoke
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
};
