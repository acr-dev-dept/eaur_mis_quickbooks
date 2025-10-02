$(document).ready(function() {
    // Ensure status hidden input exists
    if ($('#status-filter-input').length === 0) {
        $("body").append('<input type="hidden" id="status-filter-input">');
    }

    const table = $('#invoices-table').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/mis_invoices/get_mis_invoices',
            type: 'GET',
            data: function(d) {
                d.search = $('#status-filter-input').val() || '';
            }
        },
        columns: [
            { data: 'id' },
            { data: 'reg_no' },
            { data: 'reference_number', defaultContent: '-' },
            { data: 'dept', defaultContent: 0 },
            { data: 'balance', defaultContent: 0 },
            { data: 'invoice_date', defaultContent: '-' },
            {
                data: 'status',
                render: function(data) {
                    if (!data) return '-';
                    switch(data.toLowerCase()) {
                        case 'synced':
                            return '<span class="text-green-600 bg-green-100 px-2 py-1 rounded-md text-sm font-medium">Synced</span>';
                        case 'unsynced':
                            return '<span class="text-yellow-600 bg-yellow-100 px-2 py-1 rounded-md text-sm font-medium">Unsynced</span>';
                        case 'failed':
                            return '<span class="text-red-600 bg-red-100 px-2 py-1 rounded-md text-sm font-medium">Failed</span>';
                        default:
                            return '<span class="badge badge-secondary">' + data + '</span>';
                    }
                }
            },
            { data: 'pushed_by', defaultContent: '-' },
            { data: 'pushed_date', defaultContent: '-' },
            { 
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    if (row.status && row.status.toLowerCase() !== 'synced') {
                        return `<button class="sync-btn bg-blue-600 text-white px-3 py-1 rounded-md text-sm font-medium" data-id="${row.id}">Sync</button>`;
                    }
                    return '<span class="text-gray-500 text-sm">N/A</span>';
                }
            }
        ],
        order: [[0, 'desc']]
    });

    // Status filter buttons
    $(".status-filter").on("click", function() {
        $(".status-filter").removeClass("ring-2 ring-blue-500");
        $(this).addClass("ring-2 ring-blue-500");

        $("#status-filter-input").val($(this).data("status") || '');
        table.ajax.reload();
    });

    // Sync button handler
    $('#invoices-table').on('click', '.sync-btn', function () {
        const btn = $(this);
        const recordId = btn.data('id');

        btn.prop('disabled', true).text('Syncing...');

        fetch(`/api/v1/invoices/sync/${recordId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: recordId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                table.ajax.reload(null, false);
            } else {
                alert(`Sync failed: ${data.details}`);
                btn.prop('disabled', false).text('Sync');
            }
        })
        .catch(err => {
            console.error(err);
            alert('Something went wrong while syncing.');
            btn.prop('disabled', false).text('Sync');
        });
    });
});
