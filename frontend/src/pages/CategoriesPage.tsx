/**
 * Categories management page
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Center,
  Button,
  IconButton,
  useToast,
  Input,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  useDisclosure,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DeleteIcon, EditIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

interface Category {
  name: string;
  count: number;
}

export const CategoriesPage = () => {
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [newName, setNewName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const toast = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isCreateOpen,
    onOpen: onCreateOpen,
    onClose: onCreateClose,
  } = useDisclosure();

  const { data: categories, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await api.get<Category[]>('/categories');
      return response.data;
    },
  });

  const renameMutation = useMutation({
    mutationFn: async ({ oldName, newName }: { oldName: string; newName: string }) => {
      const response = await api.post('/categories/rename', {
        old_name: oldName,
        new_name: newName,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      toast({
        title: 'Category renamed',
        description: `Updated ${data.updated_count} transaction(s)`,
        status: 'success',
        duration: 3000,
      });
      onClose();
      setEditingCategory(null);
      setNewName('');
    },
    onError: () => {
      toast({
        title: 'Failed to rename category',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (categoryName: string) => {
      const response = await api.delete(`/categories/${encodeURIComponent(categoryName)}`);
      return response.data;
    },
    onSuccess: (data, categoryName) => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      toast({
        title: 'Category deleted',
        description: `Removed from ${data.updated_count} transaction(s)`,
        status: 'success',
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to delete category',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setNewName(category.name);
    onOpen();
  };

  const handleRename = () => {
    if (!editingCategory || !newName.trim()) {
      toast({
        title: 'New name is required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    renameMutation.mutate({
      oldName: editingCategory.name,
      newName: newName.trim(),
    });
  };

  const handleDelete = (category: Category) => {
    if (category.count > 0) {
      toast({
        title: 'Cannot delete category',
        description: `This category is used by ${category.count} transaction(s). Please reassign or delete those transactions first.`,
        status: 'warning',
        duration: 5000,
      });
      return;
    }

    if (window.confirm(`Are you sure you want to delete "${category.name}"?`)) {
      deleteMutation.mutate(category.name);
    }
  };

  const handleCreateNew = () => {
    setIsCreating(true);
    setNewCategoryName('');
    onCreateOpen();
  };

  const handleCreateCategory = () => {
    if (!newCategoryName.trim()) {
      toast({
        title: 'Category name is required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    // Check if category already exists
    if (categories?.some(c => c.name.toLowerCase() === newCategoryName.trim().toLowerCase())) {
      toast({
        title: 'Category already exists',
        description: `"${newCategoryName}" already exists in your categories.`,
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    // Just close the modal - the category will be created when assigned to a transaction
    toast({
      title: 'Category ready',
      description: `"${newCategoryName}" will be created when you assign it to a transaction.`,
      status: 'info',
      duration: 4000,
    });
    onCreateClose();
    setNewCategoryName('');
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg">Categories</Heading>
            <Text color="gray.600" mt={2}>
              Manage transaction categories. {categories?.length || 0} unique
              categor{categories?.length === 1 ? 'y' : 'ies'}.
            </Text>
          </Box>
          <HStack spacing={2}>
            <Button colorScheme="brand" onClick={handleCreateNew}>
              Create New
            </Button>
            <Button variant="ghost" onClick={() => navigate('/transactions')}>
              Back to Transactions
            </Button>
          </HStack>
        </HStack>

        {categories && categories.length === 0 ? (
          <Box
            bg="white"
            p={12}
            borderRadius="lg"
            boxShadow="sm"
            textAlign="center"
          >
            <Text fontSize="lg" color="gray.600" mb={4}>
              No categories yet
            </Text>
            <Text color="gray.500" mb={6}>
              Categories are created automatically when you assign them to
              transactions
            </Text>
            <Button colorScheme="brand" onClick={() => navigate('/transactions')}>
              Go to Transactions
            </Button>
          </Box>
        ) : (
          <Box bg="white" borderRadius="lg" boxShadow="sm" overflow="hidden">
            <Table variant="simple">
              <Thead bg="gray.50">
                <Tr>
                  <Th>Category Name</Th>
                  <Th isNumeric>Transactions</Th>
                  <Th width="120px">Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {categories?.map((category) => (
                  <Tr key={category.name} _hover={{ bg: 'gray.50' }}>
                    <Td>
                      <Text fontWeight="medium">{category.name}</Text>
                    </Td>
                    <Td isNumeric>
                      <Text color="gray.600">{category.count}</Text>
                    </Td>
                    <Td>
                      <HStack spacing={2}>
                        <IconButton
                          icon={<EditIcon />}
                          aria-label="Rename category"
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEdit(category)}
                        />
                        <IconButton
                          icon={<DeleteIcon />}
                          aria-label="Delete category"
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => handleDelete(category)}
                          isLoading={deleteMutation.isPending}
                          isDisabled={category.count > 0}
                          title={
                            category.count > 0
                              ? `Cannot delete - used by ${category.count} transaction(s)`
                              : 'Delete category'
                          }
                        />
                      </HStack>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </VStack>

      {/* Rename Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Rename Category</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Current Name</FormLabel>
                <Input value={editingCategory?.name || ''} isReadOnly bg="gray.50" />
              </FormControl>
              <FormControl>
                <FormLabel>New Name</FormLabel>
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Enter new category name"
                  autoFocus
                />
              </FormControl>
              <Text fontSize="sm" color="gray.600">
                This will update {editingCategory?.count} transaction(s) with the new
                category name.
              </Text>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleRename}
              isLoading={renameMutation.isPending}
            >
              Rename
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Create Modal */}
      <Modal isOpen={isCreateOpen} onClose={onCreateClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create New Category</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Category Name</FormLabel>
                <Input
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  placeholder="Enter category name"
                  autoFocus
                />
              </FormControl>
              <Text fontSize="sm" color="gray.600">
                The category will be available to assign to transactions. It will appear
                in the categories list once assigned to at least one transaction.
              </Text>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCreateClose}>
              Cancel
            </Button>
            <Button colorScheme="brand" onClick={handleCreateCategory}>
              Create
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
};
