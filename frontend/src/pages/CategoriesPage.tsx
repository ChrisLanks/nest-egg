/**
 * Categories and Labels management page with hierarchical support
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
  Select,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  AlertDialogCloseButton,
  Alert,
  AlertIcon,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  AlertDescription,
} from "@chakra-ui/react";
import React, { useState, useMemo, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DeleteIcon, EditIcon, ChevronRightIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { TableSkeleton } from "../components/LoadingSkeleton";
import { EmptyState } from "../components/EmptyState";
import { FiTag } from "react-icons/fi";
import { useUserView } from "../contexts/UserViewContext";
import HelpHint from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";

interface Category {
  id: string | null; // null for Plaid categories not yet in DB
  name: string;
  color?: string;
  parent_category_id?: string;
  is_custom: boolean; // false for Plaid categories
  transaction_count: number;
  created_at?: string;
  updated_at?: string;
}

interface CategoryWithChildren extends Category {
  children?: Category[];
}

interface Label {
  id: string;
  name: string;
  color?: string;
  is_income?: boolean | null;
  is_system?: boolean;
  parent_label_id?: string | null;
  transaction_count?: number;
}

// ── Categories Tab ───────────────────────────────────────────────────────────

const CategoriesTab = () => {
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [categoryToDelete, setCategoryToDelete] = useState<Category | null>(
    null,
  );
  const [formData, setFormData] = useState({
    name: "",
    color: "#3B82F6",
    parent_category_id: "",
    plaid_category_name: "",
  });
  const toast = useToast();
  const queryClient = useQueryClient();
  const { canWriteResource, selectedUserId, effectiveUserId } = useUserView();
  const canEdit = canWriteResource("category");
  const cancelRef = useRef<HTMLButtonElement>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isCreateOpen,
    onOpen: onCreateOpen,
    onClose: onCreateClose,
  } = useDisclosure();
  const {
    isOpen: isDeleteAlertOpen,
    onOpen: onDeleteAlertOpen,
    onClose: onDeleteAlertClose,
  } = useDisclosure();

  const { data: categories, isLoading, isError } = useQuery({
    queryKey: ["categories", effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedUserId) {
        params.user_id = effectiveUserId;
      }
      const response = await api.get<Category[]>("/categories/", { params });
      return response.data;
    },
  });

  // Organize categories into hierarchical structure (custom categories only)
  const { customCategories, plaidCategories } = useMemo(() => {
    if (!categories) return { customCategories: [], plaidCategories: [] };

    const custom = categories.filter((c) => c.is_custom);
    const plaid = categories.filter((c) => !c.is_custom);

    const categoryMap = new Map<string, CategoryWithChildren>();
    const roots: CategoryWithChildren[] = [];

    // Create map of all custom categories
    custom.forEach((category) => {
      if (category.id) {
        categoryMap.set(category.id, { ...category, children: [] });
      }
    });

    // Build hierarchy for custom categories
    custom.forEach((category) => {
      if (!category.id) return;

      const categoryWithChildren = categoryMap.get(category.id)!;
      if (category.parent_category_id) {
        const parent = categoryMap.get(category.parent_category_id);
        if (parent) {
          parent.children!.push(categoryWithChildren);
        } else {
          // Parent doesn't exist, treat as root
          roots.push(categoryWithChildren);
        }
      } else {
        roots.push(categoryWithChildren);
      }
    });

    return { customCategories: roots, plaidCategories: plaid };
  }, [categories]);

  // Get only parent categories for dropdown (custom categories only)
  const parentCategories = useMemo(() => {
    return (
      categories?.filter((c) => c.is_custom && !c.parent_category_id) || []
    );
  }, [categories]);

  const createMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const payload = {
        name: data.name,
        color: data.color || null,
        parent_category_id: data.parent_category_id || null,
      };
      const response = await api.post("/categories/", payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["infinite-transactions"] });
      toast({
        title: "Category created",
        status: "success",
        duration: 3000,
      });
      onCreateClose();
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: "Failed to create category",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: typeof formData }) => {
      const payload = {
        name: data.name || undefined,
        color: data.color || undefined,
        parent_category_id: data.parent_category_id || null,
      };
      const response = await api.patch(`/categories/${id}`, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["infinite-transactions"] });
      toast({
        title: "Category updated",
        status: "success",
        duration: 3000,
      });
      onClose();
      setEditingCategory(null);
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update category",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (categoryId: string) => {
      await api.delete(`/categories/${categoryId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["infinite-transactions"] });
      toast({
        title: "Category deleted",
        status: "success",
        duration: 3000,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to delete category",
        description:
          error.response?.data?.detail ||
          "Cannot delete category with children or transactions",
        status: "error",
        duration: 5000,
      });
    },
  });

  const resetForm = () => {
    setFormData({
      name: "",
      color: "#3B82F6",
      parent_category_id: "",
      plaid_category_name: "",
    });
  };

  const handleCreate = () => {
    resetForm();
    onCreateOpen();
  };

  const handleEdit = (category: Category) => {
    if (!category.is_custom) {
      // Converting Plaid category to custom category
      setEditingCategory(null); // No ID yet, will be created
      setFormData({
        name: category.name,
        color: "#3B82F6",
        parent_category_id: "",
        plaid_category_name: category.name, // Link to original Plaid category
      });
      onCreateOpen(); // Use create modal
    } else {
      // Editing existing custom category
      setEditingCategory(category);
      setFormData({
        name: category.name,
        color: category.color || "#3B82F6",
        parent_category_id: category.parent_category_id || "",
        plaid_category_name: "",
      });
      onOpen();
    }
  };

  const handleSubmitCreate = () => {
    if (!formData.name.trim()) {
      toast({
        title: "Name is required",
        status: "warning",
        duration: 3000,
      });
      return;
    }
    createMutation.mutate(formData);
  };

  const handleSubmitEdit = () => {
    if (!editingCategory || !formData.name.trim()) {
      toast({
        title: "Name is required",
        status: "warning",
        duration: 3000,
      });
      return;
    }
    updateMutation.mutate({ id: editingCategory.id || "", data: formData });
  };

  const handleDelete = (category: Category) => {
    if (!category.id) {
      toast({
        title: "Cannot delete Plaid category",
        description: "Convert it to a custom category first",
        status: "warning",
        duration: 3000,
      });
      return;
    }

    setCategoryToDelete(category);
    onDeleteAlertOpen();
  };

  const confirmDelete = () => {
    if (categoryToDelete?.id) {
      deleteMutation.mutate(categoryToDelete.id);
    }
    onDeleteAlertClose();
    setCategoryToDelete(null);
  };

  const renderCategoryRow = (
    category: CategoryWithChildren,
    isChild: boolean = false,
  ): JSX.Element => {
    const isPlaid = !category.is_custom;

    return (
      <React.Fragment key={category.id || category.name}>
        <Tr _hover={{ bg: "bg.subtle" }}>
          <Td>
            <HStack spacing={2}>
              {isChild && <ChevronRightIcon ml={4} color="text.muted" />}
              <Box
                w={3}
                h={3}
                borderRadius="sm"
                bg={category.color || (isPlaid ? "gray.300" : "gray.400")}
              />
              <Text fontWeight={isChild ? "normal" : "semibold"}>
                {category.name}
              </Text>
              {isPlaid && (
                <Text fontSize="xs" color="text.muted">
                  (from your bank)
                </Text>
              )}
            </HStack>
          </Td>
          <Td>
            <Text fontSize="sm" color="text.secondary">
              {category.transaction_count} transaction
              {category.transaction_count !== 1 ? "s" : ""}
            </Text>
          </Td>
          <Td>
            <HStack spacing={2}>
              {isPlaid ? (
                <Button
                  size="sm"
                  colorScheme="blue"
                  variant="ghost"
                  isDisabled={!canEdit}
                  onClick={() => handleEdit(category)}
                >
                  Make Custom
                </Button>
              ) : (
                <>
                  <IconButton
                    icon={<EditIcon />}
                    aria-label="Edit category"
                    size="sm"
                    variant="ghost"
                    isDisabled={!canEdit}
                    onClick={() => handleEdit(category)}
                  />
                  <IconButton
                    icon={<DeleteIcon />}
                    aria-label="Delete category"
                    size="sm"
                    variant="ghost"
                    colorScheme="red"
                    isDisabled={!canEdit}
                    onClick={() => handleDelete(category)}
                    isLoading={deleteMutation.isPending}
                  />
                </>
              )}
            </HStack>
          </Td>
        </Tr>
        {category.children?.map((child: CategoryWithChildren) =>
          renderCategoryRow(child, true),
        )}
      </React.Fragment>
    );
  };

  if (isLoading) {
    return <TableSkeleton />;
  }

  if (isError) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        Failed to load categories. Please refresh and try again.
      </Alert>
    );
  }

  return (
    <>
      <HStack justify="space-between" align="start">
        <Box>
          <Heading size="lg">Categories</Heading>
          <Text color="text.secondary" mt={2}>
            {localStorage.getItem("nest-egg-show-advanced-nav") === "true"
              ? "Organize transactions by category and sub-category. Separate from labels."
              : "Group transactions by topic — like \"Groceries\" or \"Rent\". You can nest sub-categories under a parent (e.g. Food → Dining Out). Categories are different from labels, which are free-form tags you can add to any transaction."}
          </Text>
        </Box>
        <Button
          colorScheme="brand"
          isDisabled={!canEdit}
          onClick={handleCreate}
        >
          Create Category
        </Button>
      </HStack>

      {customCategories.length === 0 && plaidCategories.length === 0 ? (
        <EmptyState
          icon={FiTag}
          title="No categories yet"
          description="Create categories to organize your transactions and track spending patterns."
          actionLabel="Create Your First Category"
          onAction={handleCreate}
        />
      ) : (
        <Box
          bg="bg.surface"
          borderRadius="lg"
          boxShadow="sm"
          overflowX="auto"
        >
          <Table variant="simple" size="sm">
            <Thead bg="bg.subtle">
              <Tr>
                <Th>Category Name</Th>
                <Th width="150px">Transactions</Th>
                <Th width="200px">Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {/* Custom Categories (hierarchical) */}
              {customCategories.length > 0 && (
                <>
                  <Tr bg="bg.muted">
                    <Td colSpan={3}>
                      <Text
                        fontWeight="bold"
                        fontSize="sm"
                        color="text.heading"
                      >
                        Custom Categories
                      </Text>
                    </Td>
                  </Tr>
                  {customCategories.map((category) =>
                    renderCategoryRow(category),
                  )}
                </>
              )}

              {/* Plaid Categories (flat) */}
              {plaidCategories.length > 0 && (
                <>
                  <Tr bg="bg.muted">
                    <Td colSpan={3}>
                      <Text
                        fontWeight="bold"
                        fontSize="sm"
                        color="text.heading"
                      >
                        Provider Categories (click "Make Custom" to edit)
                        <HelpHint
                          hint={helpContent.categories.providerCategories}
                        />
                      </Text>
                    </Td>
                  </Tr>
                  {plaidCategories.map((category) =>
                    renderCategoryRow(category),
                  )}
                </>
              )}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Create Modal */}
      <Modal isOpen={isCreateOpen} onClose={onCreateClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create New Category</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Category Name</FormLabel>
                <Input
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Enter category name"
                  autoFocus
                />
              </FormControl>

              <FormControl>
                <FormLabel>Parent Category (Optional)</FormLabel>
                <Select
                  value={formData.parent_category_id}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      parent_category_id: e.target.value,
                    })
                  }
                  placeholder="None (Root level)"
                >
                  {parentCategories.map((category) => (
                    <option key={category.id} value={category.id || ""}>
                      {category.name}
                    </option>
                  ))}
                </Select>
                <Text fontSize="xs" color="text.muted" mt={1}>
                  Categories can only be nested 2 levels deep (parent → child)
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Color</FormLabel>
                <Input
                  type="color"
                  value={formData.color}
                  onChange={(e) =>
                    setFormData({ ...formData, color: e.target.value })
                  }
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCreateClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleSubmitCreate}
              isLoading={createMutation.isPending}
            >
              Create
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Edit Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Edit Category</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Category Name</FormLabel>
                <Input
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Enter category name"
                  autoFocus
                />
              </FormControl>

              <FormControl>
                <FormLabel>Parent Category (Optional)</FormLabel>
                <Select
                  value={formData.parent_category_id}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      parent_category_id: e.target.value,
                    })
                  }
                  placeholder="None (Root level)"
                >
                  {parentCategories
                    .filter((c) => c.id !== editingCategory?.id)
                    .map((category) => (
                      <option key={category.id} value={category.id || ""}>
                        {category.name}
                      </option>
                    ))}
                </Select>
                <Text fontSize="xs" color="text.muted" mt={1}>
                  Cannot make this a child if it already has children
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Color</FormLabel>
                <Input
                  type="color"
                  value={formData.color}
                  onChange={(e) =>
                    setFormData({ ...formData, color: e.target.value })
                  }
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleSubmitEdit}
              isLoading={updateMutation.isPending}
            >
              Save Changes
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        isOpen={isDeleteAlertOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeleteAlertClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Category
            </AlertDialogHeader>
            <AlertDialogCloseButton />

            <AlertDialogBody>
              Are you sure you want to delete{" "}
              <strong>"{categoryToDelete?.name}"</strong>?
              {categoryToDelete && categoryToDelete.transaction_count > 0 && (
                <Text mt={2} color="orange.600">
                  This category is used by {categoryToDelete.transaction_count}{" "}
                  transaction(s). It will be removed from all of them.
                </Text>
              )}
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteAlertClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={confirmDelete}
                ml={3}
                isLoading={deleteMutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
};

// ── Labels Tab ───────────────────────────────────────────────────────────────

type LabelIncomeState = "income" | "expense" | "any";

function incomeStateToValue(state: LabelIncomeState): boolean | null {
  if (state === "income") return true;
  if (state === "expense") return false;
  return null;
}

function valueToIncomeState(value: boolean | null | undefined): LabelIncomeState {
  if (value === true) return "income";
  if (value === false) return "expense";
  return "any";
}

const LabelsTab = () => {
  const [editingLabel, setEditingLabel] = useState<Label | null>(null);
  const [labelToDelete, setLabelToDelete] = useState<Label | null>(null);
  const [labelFormData, setLabelFormData] = useState({
    name: "",
    color: "#3B82F6",
    incomeState: "any" as LabelIncomeState,
    parent_label_id: "",
  });
  const toast = useToast();
  const queryClient = useQueryClient();
  const { canWriteResource } = useUserView();
  const canEdit = canWriteResource("category");
  const cancelRef = useRef<HTMLButtonElement>(null);

  const {
    isOpen: isCreateOpen,
    onOpen: onCreateOpen,
    onClose: onCreateClose,
  } = useDisclosure();
  const {
    isOpen: isEditOpen,
    onOpen: onEditOpen,
    onClose: onEditClose,
  } = useDisclosure();
  const {
    isOpen: isDeleteAlertOpen,
    onOpen: onDeleteAlertOpen,
    onClose: onDeleteAlertClose,
  } = useDisclosure();

  const { data: labels, isLoading, isError } = useQuery({
    queryKey: ["labels-all"],
    queryFn: async () => {
      const response = await api.get<Label[]>("/labels/");
      return response.data;
    },
  });

  // Root labels for the parent dropdown (max 2 levels)
  const rootLabels = useMemo(() => {
    return labels?.filter((l) => !l.parent_label_id) || [];
  }, [labels]);

  const invalidateLabels = () => {
    queryClient.invalidateQueries({ queryKey: ["labels-all"] });
    queryClient.invalidateQueries({ queryKey: ["categories"] });
  };

  const createLabelMutation = useMutation({
    mutationFn: async (data: typeof labelFormData) => {
      const payload: Record<string, unknown> = {
        name: data.name,
        color: data.color || null,
        is_income: incomeStateToValue(data.incomeState),
        parent_label_id: data.parent_label_id || null,
      };
      const response = await api.post("/labels/", payload);
      return response.data;
    },
    onSuccess: () => {
      invalidateLabels();
      toast({ title: "Label created", status: "success", duration: 3000 });
      onCreateClose();
      resetLabelForm();
    },
    onError: (error: any) => {
      toast({
        title: "Failed to create label",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  const updateLabelMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: typeof labelFormData }) => {
      const payload: Record<string, unknown> = {
        name: data.name || undefined,
        color: data.color || undefined,
        is_income: incomeStateToValue(data.incomeState),
      };
      const response = await api.patch(`/labels/${id}`, payload);
      return response.data;
    },
    onSuccess: () => {
      invalidateLabels();
      toast({ title: "Label updated", status: "success", duration: 3000 });
      onEditClose();
      setEditingLabel(null);
      resetLabelForm();
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update label",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  const deleteLabelMutation = useMutation({
    mutationFn: async (labelId: string) => {
      await api.delete(`/labels/${labelId}`);
    },
    onSuccess: () => {
      invalidateLabels();
      toast({ title: "Label deleted", status: "success", duration: 3000 });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to delete label",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  const resetLabelForm = () => {
    setLabelFormData({
      name: "",
      color: "#3B82F6",
      incomeState: "any",
      parent_label_id: "",
    });
  };

  const handleCreateLabel = () => {
    resetLabelForm();
    onCreateOpen();
  };

  const handleEditLabel = (label: Label) => {
    setEditingLabel(label);
    setLabelFormData({
      name: label.name,
      color: label.color || "#3B82F6",
      incomeState: valueToIncomeState(label.is_income),
      parent_label_id: label.parent_label_id || "",
    });
    onEditOpen();
  };

  const handleSubmitCreateLabel = () => {
    if (!labelFormData.name.trim()) {
      toast({ title: "Name is required", status: "warning", duration: 3000 });
      return;
    }
    createLabelMutation.mutate(labelFormData);
  };

  const handleSubmitEditLabel = () => {
    if (!editingLabel || !labelFormData.name.trim()) {
      toast({ title: "Name is required", status: "warning", duration: 3000 });
      return;
    }
    updateLabelMutation.mutate({ id: editingLabel.id, data: labelFormData });
  };

  const handleDeleteLabel = (label: Label) => {
    if (label.is_system) {
      toast({
        title: "Cannot delete system label",
        description: "System labels cannot be removed.",
        status: "warning",
        duration: 3000,
      });
      return;
    }
    setLabelToDelete(label);
    onDeleteAlertOpen();
  };

  const confirmDeleteLabel = () => {
    if (labelToDelete?.id) {
      deleteLabelMutation.mutate(labelToDelete.id);
    }
    onDeleteAlertClose();
    setLabelToDelete(null);
  };

  const getParentName = (label: Label): string => {
    if (!label.parent_label_id) return "—";
    const parent = labels?.find((l) => l.id === label.parent_label_id);
    return parent?.name || "—";
  };

  const getTypeLabel = (label: Label): string => {
    if (label.is_income === true) return "Income";
    if (label.is_income === false) return "Expense";
    return "Any";
  };

  if (isLoading) {
    return <TableSkeleton />;
  }

  if (isError) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        Failed to load labels. Please refresh and try again.
      </Alert>
    );
  }

  const LabelFormFields = () => (
    <VStack spacing={4}>
      <FormControl isRequired>
        <FormLabel>Label Name</FormLabel>
        <Input
          value={labelFormData.name}
          onChange={(e) =>
            setLabelFormData({ ...labelFormData, name: e.target.value })
          }
          placeholder="Enter label name"
          autoFocus
        />
      </FormControl>

      <FormControl>
        <FormLabel>Type</FormLabel>
        <Select
          value={labelFormData.incomeState}
          onChange={(e) =>
            setLabelFormData({
              ...labelFormData,
              incomeState: e.target.value as LabelIncomeState,
            })
          }
        >
          <option value="any">Any (Income or Expense)</option>
          <option value="income">Income</option>
          <option value="expense">Expense</option>
        </Select>
      </FormControl>

      <FormControl>
        <FormLabel>Color</FormLabel>
        <Input
          type="color"
          value={labelFormData.color}
          onChange={(e) =>
            setLabelFormData({ ...labelFormData, color: e.target.value })
          }
        />
      </FormControl>
    </VStack>
  );

  return (
    <>
      <HStack justify="space-between" align="start">
        <Box>
          <Heading size="lg">Labels</Heading>
          <Text color="text.secondary" mt={2}>
            Manage freeform tags applied to transactions across categories.
          </Text>
        </Box>
        <Button
          colorScheme="brand"
          isDisabled={!canEdit}
          onClick={handleCreateLabel}
        >
          Create Label
        </Button>
      </HStack>

      {!labels || labels.length === 0 ? (
        <EmptyState
          icon={FiTag}
          title="No labels yet"
          description="Create labels to tag transactions for cross-cutting purposes like tax deductibility or business expenses."
          actionLabel="Create Your First Label"
          onAction={handleCreateLabel}
        />
      ) : (
        <Box
          bg="bg.surface"
          borderRadius="lg"
          boxShadow="sm"
          overflowX="auto"
        >
          <Table variant="simple" size="sm">
            <Thead bg="bg.subtle">
              <Tr>
                <Th>Name</Th>
                <Th width="120px">Type</Th>
                <Th width="150px">Parent</Th>
                <Th width="150px">Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {labels.map((label) => (
                <Tr key={label.id} _hover={{ bg: "bg.subtle" }}>
                  <Td>
                    <HStack spacing={2}>
                      {label.parent_label_id && (
                        <ChevronRightIcon ml={4} color="text.muted" />
                      )}
                      <Box
                        w={3}
                        h={3}
                        borderRadius="sm"
                        bg={label.color || "gray.400"}
                        flexShrink={0}
                      />
                      <Text fontWeight={label.parent_label_id ? "normal" : "semibold"}>
                        {label.name}
                      </Text>
                      {label.is_system && (
                        <Text fontSize="xs" color="text.muted">
                          (system)
                        </Text>
                      )}
                    </HStack>
                  </Td>
                  <Td>
                    <Text fontSize="sm" color="text.secondary">
                      {getTypeLabel(label)}
                    </Text>
                  </Td>
                  <Td>
                    <Text fontSize="sm" color="text.secondary">
                      {getParentName(label)}
                    </Text>
                  </Td>
                  <Td>
                    <HStack spacing={2}>
                      <IconButton
                        icon={<EditIcon />}
                        aria-label="Edit label"
                        size="sm"
                        variant="ghost"
                        isDisabled={!canEdit}
                        onClick={() => handleEditLabel(label)}
                      />
                      <IconButton
                        icon={<DeleteIcon />}
                        aria-label="Delete label"
                        size="sm"
                        variant="ghost"
                        colorScheme="red"
                        isDisabled={!canEdit || !!label.is_system}
                        onClick={() => handleDeleteLabel(label)}
                        isLoading={deleteLabelMutation.isPending}
                      />
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Create Label Modal */}
      <Modal isOpen={isCreateOpen} onClose={onCreateClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create New Label</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Label Name</FormLabel>
                <Input
                  value={labelFormData.name}
                  onChange={(e) =>
                    setLabelFormData({ ...labelFormData, name: e.target.value })
                  }
                  placeholder="Enter label name"
                  autoFocus
                />
              </FormControl>

              <FormControl>
                <FormLabel>Type</FormLabel>
                <Select
                  value={labelFormData.incomeState}
                  onChange={(e) =>
                    setLabelFormData({
                      ...labelFormData,
                      incomeState: e.target.value as LabelIncomeState,
                    })
                  }
                >
                  <option value="any">Any (Income or Expense)</option>
                  <option value="income">Income</option>
                  <option value="expense">Expense</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Parent Label (Optional)</FormLabel>
                <Select
                  value={labelFormData.parent_label_id}
                  onChange={(e) =>
                    setLabelFormData({
                      ...labelFormData,
                      parent_label_id: e.target.value,
                    })
                  }
                  placeholder="None (Root level)"
                >
                  {rootLabels.map((label) => (
                    <option key={label.id} value={label.id}>
                      {label.name}
                    </option>
                  ))}
                </Select>
                <Text fontSize="xs" color="text.muted" mt={1}>
                  Labels can only be nested 2 levels deep (parent → child)
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Color</FormLabel>
                <Input
                  type="color"
                  value={labelFormData.color}
                  onChange={(e) =>
                    setLabelFormData({ ...labelFormData, color: e.target.value })
                  }
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCreateClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleSubmitCreateLabel}
              isLoading={createLabelMutation.isPending}
            >
              Create
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Edit Label Modal */}
      <Modal isOpen={isEditOpen} onClose={onEditClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Edit Label</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <LabelFormFields />
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onEditClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleSubmitEditLabel}
              isLoading={updateLabelMutation.isPending}
            >
              Save Changes
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Delete Label Confirmation Dialog */}
      <AlertDialog
        isOpen={isDeleteAlertOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeleteAlertClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Label
            </AlertDialogHeader>
            <AlertDialogCloseButton />
            <AlertDialogBody>
              Are you sure you want to delete{" "}
              <strong>"{labelToDelete?.name}"</strong>?
              {labelToDelete && (labelToDelete.transaction_count ?? 0) > 0 && (
                <Text mt={2} color="orange.600">
                  This label is used by {labelToDelete.transaction_count}{" "}
                  transaction(s). It will be removed from all of them.
                </Text>
              )}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteAlertClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={confirmDeleteLabel}
                ml={3}
                isLoading={deleteLabelMutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
};

// ── Banner text ──────────────────────────────────────────────────────────────

const CATEGORIES_BANNER =
  "Categories classify what a transaction is — Groceries, Dining, Utilities. They come from your bank (provider categories) or you can create custom ones. Used in budgets, trends, and reports.";

const LABELS_BANNER =
  'Labels are freeform tags you apply to transactions for cross-cutting purposes — "Business Expense", "Tax Deductible", "Freelance Income". A transaction can have multiple labels. Used in the Variable Income Planner, Tax Deductible page, and Rules.';

// ── Page ─────────────────────────────────────────────────────────────────────

export const CategoriesPage = () => {
  const navigate = useNavigate();
  const [tabIndex, setTabIndex] = useState(0);

  const bannerText = tabIndex === 0 ? CATEGORIES_BANNER : LABELS_BANNER;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg">Categories &amp; Labels</Heading>
            <Text color="text.secondary" mt={1}>
              Organize your transactions with categories and cross-cutting labels.
            </Text>
          </Box>
          <Button variant="ghost" onClick={() => navigate("/transactions")}>
            Back to Transactions
          </Button>
        </HStack>

        <Tabs index={tabIndex} onChange={setTabIndex} colorScheme="brand">
          <TabList>
            <Tab>Categories</Tab>
            <Tab>Labels</Tab>
          </TabList>

          <Alert status="info" borderRadius="md" mt={4}>
            <AlertIcon />
            <AlertDescription>{bannerText}</AlertDescription>
          </Alert>

          <TabPanels mt={4}>
            <TabPanel px={0}>
              <VStack spacing={6} align="stretch">
                <CategoriesTab />
              </VStack>
            </TabPanel>
            <TabPanel px={0}>
              <VStack spacing={6} align="stretch">
                <LabelsTab />
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Container>
  );
};
