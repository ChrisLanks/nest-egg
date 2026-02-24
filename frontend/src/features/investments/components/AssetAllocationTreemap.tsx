/**
 * Interactive treemap for asset allocation with drill-down capability
 */

import { Box, Heading, HStack, Button, Text } from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { Treemap, ResponsiveContainer } from 'recharts';

interface TreemapNode {
  name: string;
  value: number;
  percent: number;
  children?: TreemapNode[];
  color?: string;
  [key: string]: any; // Index signature for Recharts compatibility
}

interface AssetAllocationTreemapProps {
  data: TreemapNode;
  onDrillDown?: (node: TreemapNode | null) => void;
}

const COLORS = {
  stocks: '#4299E1', // blue
  bonds: '#48BB78', // green
  realEstate: '#ED8936', // orange
  crypto: '#9F7AEA', // purple
  cash: '#38B2AC', // teal
  other: '#A0AEC0', // gray
  domestic: '#3182CE',
  international: '#805AD5',
  etf: '#319795',
  mutualFund: '#D69E2E',
};

export const AssetAllocationTreemap = ({ data, onDrillDown }: AssetAllocationTreemapProps) => {
  const [breadcrumbs, setBreadcrumbs] = useState<TreemapNode[]>([]);
  const [currentNode, setCurrentNode] = useState<TreemapNode>(data);

  // Sync currentNode when data prop changes (e.g., when portfolio updates)
  useEffect(() => {
    setCurrentNode(data);
    setBreadcrumbs([]);
    onDrillDown?.(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]); // Only re-run when data changes, not when onDrillDown callback changes

  console.log('🎨 AssetAllocationTreemap render');
  console.log('   Root data:', data);
  console.log('   Root children count:', data.children?.length || 0);
  console.log('   Current node:', currentNode.name);
  console.log('   Current children count:', currentNode.children?.length || 0);

  // Log each child node details
  if (currentNode.children) {
    console.log('   Children details:');
    currentNode.children.forEach((child, i) => {
      console.log(`     [${i}] ${child.name}: $${child.value} (${child.percent}%) - children: ${child.children?.length || 0}`);
    });
  }

  const handleRectClick = (clickedName: string) => {
    console.log('🖱️ Rectangle clicked:', clickedName);

    // Find the child node with this name from our actual data
    const childNode = currentNode.children?.find(child => child.name === clickedName);

    console.log('   Found node:', childNode);
    console.log('   Has children:', childNode?.children?.length || 0);

    if (childNode?.children && childNode.children.length > 0) {
      console.log('   ✅ Drilling down to:', childNode.name);
      setBreadcrumbs([...breadcrumbs, currentNode]);
      setCurrentNode(childNode);
      onDrillDown?.(childNode);
    } else {
      console.log('   ⚠️ No children to drill down to');
    }
  };

  const handleBreadcrumbClick = (index: number) => {
    if (index === -1) {
      // Go back to root
      setCurrentNode(data);
      setBreadcrumbs([]);
      onDrillDown?.(null);
    } else {
      // Go back to specific level
      const newNode = breadcrumbs[index];
      setCurrentNode(newNode);
      setBreadcrumbs(breadcrumbs.slice(0, index));
      onDrillDown?.(newNode);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const CustomizedContent = (props: any) => {
    const { x, y, width, height, name, value, percent, fill, color } = props;

    // Skip empty container nodes that Recharts creates
    if (!name) {
      return null;
    }

    // Find the actual node data from our currentNode.children array to check for children
    const nodeData = currentNode.children?.find(child => child.name === name);
    const hasChildren = nodeData?.children && nodeData.children.length > 0;

    console.log('📦 CustomizedContent render:', {
      name,
      value,
      hasChildren,
      lookupChildren: nodeData?.children?.length || 0,
    });

    // Only show label if box is large enough
    const showLabel = width > 60 && height > 40;
    const showPercent = width > 80 && height > 50;

    // Calculate percent if not provided (shouldn't happen, but safety check)
    const displayPercent = percent || 0;

    const handleClick = (e: React.MouseEvent) => {
      console.log('🎯 CLICK EVENT FIRED on:', name);
      e.stopPropagation();
      if (hasChildren) {
        handleRectClick(name);
      } else {
        console.log('   ⚠️ No children, ignoring click');
      }
    };

    return (
      <g>
        <title>{`${name}\n${formatCurrency(value)} (${Number(percent).toFixed(1)}%)`}</title>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          style={{
            fill: color || fill,
            stroke: '#fff',
            strokeWidth: 2,
            cursor: hasChildren ? 'pointer' : 'default',
            transition: 'opacity 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '0.8';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = '1';
          }}
          onClick={handleClick}
        />
        {showLabel && name && (
          <g pointerEvents="none">
            <text
              x={x + width / 2}
              y={y + height / 2 - (showPercent ? 8 : 0)}
              textAnchor="middle"
              fill="#fff"
              fontSize={width > 100 ? 14 : 11}
              fontWeight="bold"
            >
              {name}
            </text>
            {showPercent && (
              <>
                <text
                  x={x + width / 2}
                  y={y + height / 2 + 6}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize={11}
                >
                  {formatCurrency(value)}
                </text>
                <text
                  x={x + width / 2}
                  y={y + height / 2 + 20}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize={10}
                >
                  {Number(displayPercent).toFixed(1)}%
                </text>
              </>
            )}
          </g>
        )}
      </g>
    );
  };

  return (
    <Box>
      {/* Breadcrumb Navigation */}
      {breadcrumbs.length > 0 && (
        <HStack mb={4} spacing={2}>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleBreadcrumbClick(-1)}
          >
            All Assets
          </Button>
          {breadcrumbs.map((crumb, index) => (
            <HStack key={index} spacing={2}>
              <Text color="text.muted">/</Text>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleBreadcrumbClick(index)}
              >
                {crumb.name}
              </Button>
            </HStack>
          ))}
          {currentNode !== data && (
            <>
              <Text color="text.muted">/</Text>
              <Text fontWeight="bold">{currentNode.name}</Text>
            </>
          )}
        </HStack>
      )}

      {/* Current Level Title */}
      <Heading size="md" mb={4}>
        {currentNode.name} - {formatCurrency(currentNode.value)}
      </Heading>

      {/* Treemap */}
      <ResponsiveContainer width="100%" height={400}>
        {currentNode.children && currentNode.children.length > 0 ? (
          <Treemap
            data={currentNode.children.map(child => ({
              name: child.name,
              value: child.value,
              percent: child.percent,
              color: child.color,
              // Strip children to show only one level at a time
            }))}
            dataKey="value"
            stroke="#fff"
            fill="#8884d8"
            content={<CustomizedContent />}
            isAnimationActive={true}
            animationDuration={200}
          />
        ) : (
          <Text fontSize="sm" color="text.secondary" textAlign="center" py={8}>
            No data to display
          </Text>
        )}
      </ResponsiveContainer>

      {/* Legend */}
      {currentNode.children && currentNode.children.length > 0 && (
        <Box mt={4}>
          <Text fontSize="sm" fontWeight="semibold" mb={2} color="text.heading">
            Categories:
          </Text>
          <HStack spacing={3} flexWrap="wrap">
            {currentNode.children.map((child) => (
              <HStack key={child.name} spacing={1}>
                <Box
                  w="12px"
                  h="12px"
                  bg={child.color}
                  borderRadius="2px"
                />
                <Text fontSize="sm" color="text.heading">
                  {child.name}: {child.percent.toFixed(1)}%
                </Text>
              </HStack>
            ))}
          </HStack>
        </Box>
      )}

      {/* Help Text */}
      {currentNode.children && currentNode.children.length > 0 && (
        <Text fontSize="sm" color="text.secondary" mt={2}>
          Click on a category to drill down
        </Text>
      )}
    </Box>
  );
};
