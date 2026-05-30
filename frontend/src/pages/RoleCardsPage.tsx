import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/api/client';
import type { RoleCard, RoleCardCreate } from '@/types';
import RoleCardList from '@/components/role-card/RoleCardList';
import RoleCardForm from '@/components/role-card/RoleCardForm';
import RoleCardPreview from '@/components/role-card/RoleCardPreview';

export default function RoleCardsPage() {
  const [roleCards, setRoleCards] = useState<RoleCard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingRoleCard, setEditingRoleCard] = useState<RoleCard | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [previewRoleCard, setPreviewRoleCard] = useState<RoleCard | null>(null);
  const [copyTarget, setCopyTarget] = useState<RoleCard | null>(null);

  const fetchRoleCards = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient.getRoleCards();
      setRoleCards(data as RoleCard[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载角色卡列表失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoleCards();
  }, [fetchRoleCards]);

  const handleCreate = async (data: RoleCardCreate) => {
    try {
      setIsSubmitting(true);
      await apiClient.createRoleCard(data);
      setShowForm(false);
      await fetchRoleCards();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建角色卡失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async (data: RoleCardCreate) => {
    if (!editingRoleCard) return;

    try {
      setIsSubmitting(true);
      await apiClient.updateRoleCard(editingRoleCard.id, data);
      setEditingRoleCard(null);
      setShowForm(false);
      await fetchRoleCards();
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新角色卡失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (roleCardId: string) => {
    try {
      await apiClient.deleteRoleCard(roleCardId);
      await fetchRoleCards();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除角色卡失败');
    }
  };

  const handleEdit = (roleCard: RoleCard) => {
    setEditingRoleCard(roleCard);
    setShowForm(true);
  };

  const handleCopy = (roleCard: RoleCard) => {
    setCopyTarget(roleCard);
  };

  const handleCopyConfirm = async () => {
    if (!copyTarget) return;
    const newName = window.prompt(`复制 "${copyTarget.name}"，请输入新名称：`, `${copyTarget.name} (副本)`);
    if (!newName) return;

    try {
      setIsSubmitting(true);
      await apiClient.copyRoleCard(copyTarget.id, newName);
      setCopyTarget(null);
      await fetchRoleCards();
    } catch (err) {
      setError(err instanceof Error ? err.message : '复制角色卡失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setEditingRoleCard(null);
    setShowForm(false);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">角色卡管理</h1>
          <p className="text-sm text-gray-500 mt-1">
            创建和管理 AI 专家角色，定义专业领域、职责和系统提示词
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            + 添加角色卡
          </button>
        )}
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {showForm && (
        <div className="mb-6 bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            {editingRoleCard ? '编辑角色卡' : '添加角色卡'}
          </h2>
          <RoleCardForm
            roleCard={editingRoleCard ?? undefined}
            onSubmit={editingRoleCard ? handleUpdate : handleCreate}
            onCancel={handleCancel}
            isSubmitting={isSubmitting}
          />
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-gray-500">加载中...</p>
        </div>
      ) : (
        <RoleCardList
          roleCards={roleCards}
          onEdit={handleEdit}
          onCopy={handleCopy}
          onDelete={handleDelete}
          onPreview={setPreviewRoleCard}
        />
      )}

      {copyTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black bg-opacity-50"
            onClick={() => setCopyTarget(null)}
          />
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">复制角色卡</h3>
            <p className="text-sm text-gray-500 mb-4">
              将复制 <span className="font-medium text-gray-700">"{copyTarget.name}"</span> 的所有配置。
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setCopyTarget(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                取消
              </button>
              <button
                onClick={handleCopyConfirm}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {isSubmitting ? '复制中...' : '确认复制'}
              </button>
            </div>
          </div>
        </div>
      )}

      {previewRoleCard && (
        <RoleCardPreview
          roleCard={previewRoleCard}
          onClose={() => setPreviewRoleCard(null)}
        />
      )}
    </div>
  );
}
