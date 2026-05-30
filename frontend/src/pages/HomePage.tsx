import { Link } from 'react-router-dom';

const cards = [
  {
    title: 'Provider 设置',
    description: '配置 LLM API 提供商，管理 API 密钥和模型参数',
    path: '/settings',
    icon: '⚙️',
    color: 'bg-blue-50 hover:bg-blue-100 border-blue-200',
  },
  {
    title: '角色卡管理',
    description: '创建和管理专家角色卡，定义专业领域和行为约束',
    path: '/role-cards',
    icon: '👤',
    color: 'bg-green-50 hover:bg-green-100 border-green-200',
  },
  {
    title: '专家讨论室',
    description: '创建讨论室，邀请专家协作完成任务',
    path: '/rooms',
    icon: '💬',
    color: 'bg-purple-50 hover:bg-purple-100 border-purple-200',
  },
];

export default function HomePage() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          专家团
        </h1>
        <p className="text-lg text-gray-600">
          AI 专家协作工作台 — 让多个 AI 专家共同讨论并产出高质量文档
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {cards.map((card) => (
          <Link
            key={card.path}
            to={card.path}
            className={`block p-6 rounded-lg border transition-colors ${card.color}`}
          >
            <div className="text-3xl mb-4">{card.icon}</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {card.title}
            </h2>
            <p className="text-gray-600 text-sm">
              {card.description}
            </p>
          </Link>
        ))}
      </div>

      <div className="mt-12 p-6 bg-white rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-3">
          快速开始
        </h3>
        <ol className="space-y-2 text-gray-600 text-sm">
          <li className="flex items-start">
            <span className="font-medium text-gray-900 mr-2">1.</span>
            配置至少一个 LLM Provider（如 OpenAI、Claude）
          </li>
          <li className="flex items-start">
            <span className="font-medium text-gray-900 mr-2">2.</span>
            创建或使用内置的角色卡
          </li>
          <li className="flex items-start">
            <span className="font-medium text-gray-900 mr-2">3.</span>
            新建讨论室，选择专家和讨论策略
          </li>
          <li className="flex items-start">
            <span className="font-medium text-gray-900 mr-2">4.</span>
            开始讨论，等待专家产出最终文档
          </li>
        </ol>
      </div>
    </div>
  );
}
